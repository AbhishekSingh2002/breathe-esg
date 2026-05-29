from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Count
from datetime import datetime
import json

from apps.emissions.models import (
    Organization, DataSource, RawRecord, EmissionRecord, ReviewHistory
)
from apps.emissions.serializers import (
    OrganizationSerializer, DataSourceSerializer,
    EmissionRecordListSerializer, EmissionRecordDetailSerializer,
    EmissionRecordApproveSerializer, DashboardStatsSerializer
)
from services.sap_parser import SAPParser
from services.utility_parser import UtilityParser
from services.travel_parser import TravelParser
from services.normalizer import Normalizer


class EmissionRecordViewSet(viewsets.ModelViewSet):
    """
    Main API for emissions records.
    
    GET /api/emissions/ - list records
    GET /api/emissions/{id}/ - detail
    GET /api/emissions/dashboard/stats/ - metrics
    POST /api/emissions/{id}/approve/ - approve/reject/flag
    """
    
    permission_classes = [AllowAny]  # Allow unauthenticated access in development
    serializer_class = EmissionRecordListSerializer
    
    def get_queryset(self):
        """Filter to user's organization"""
        user = self.request.user
        org = Organization.objects.first()  # In production: get from user profile
        
        queryset = EmissionRecord.objects.filter(
            organization=org
        ).prefetch_related('review_history', 'data_source')
        
        # Filtering
        scope = self.request.query_params.get('scope')
        if scope:
            queryset = queryset.filter(scope=scope)
        
        review_status = self.request.query_params.get('review_status')
        if review_status:
            queryset = queryset.filter(review_status=review_status)
        
        source_type = self.request.query_params.get('source_type')
        if source_type:
            queryset = queryset.filter(data_source__source_type=source_type)
        
        # Ordering
        ordering = self.request.query_params.get('ordering', '-activity_date')
        queryset = queryset.order_by(ordering)
        
        return queryset
    
    def get_serializer_class(self):
        """Use detail serializer for detail views"""
        if self.action == 'retrieve':
            return EmissionRecordDetailSerializer
        return EmissionRecordListSerializer
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard metrics"""
        org = Organization.objects.first()
        queryset = EmissionRecord.objects.filter(organization=org)
        
        total_emissions = queryset.aggregate(
            total=Sum('calculated_emissions')
        )['total'] or 0
        
        emissions_by_scope = {}
        for scope in ['SCOPE_1', 'SCOPE_2', 'SCOPE_3']:
            total = queryset.filter(scope=scope).aggregate(
                total=Sum('calculated_emissions')
            )['total'] or 0
            emissions_by_scope[scope] = float(total)
        
        stats = {
            'total_records': queryset.count(),
            'pending_review': queryset.filter(review_status='PENDING').count(),
            'flagged_suspicious': queryset.filter(review_status='FLAGGED').count(),
            'approved': queryset.filter(review_status='APPROVED').count(),
            'rejected': queryset.filter(review_status='REJECTED').count(),
            'total_emissions': float(total_emissions),
            'emissions_by_scope': emissions_by_scope,
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve, reject, or flag a record.
        
        POST /api/emissions/{id}/approve/
        {
            "action": "APPROVE" | "REJECT" | "FLAG",
            "notes": "Optional explanation"
        }
        """
        record = self.get_object()
        serializer = EmissionRecordApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')
        
        # Map action to review_status
        status_map = {
            'APPROVE': 'APPROVED',
            'REJECT': 'REJECTED',
            'FLAG': 'FLAGGED',
        }
        
        old_status = record.review_status
        record.review_status = status_map[action]
        
        if action == 'APPROVE':
            record.approved_by = request.user
            record.approved_at = datetime.now()
        
        record.review_notes = notes
        record.save()
        
        # Log in history
        ReviewHistory.objects.create(
            emission_record=record,
            action=action,
            performed_by=request.user,
            notes=notes,
            changes={'review_status': old_status + ' → ' + status_map[action]}
        )
        
        return Response(
            EmissionRecordDetailSerializer(record).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    def batch_approve(self, request):
        """
        Approve multiple records at once.
        
        POST /api/emissions/batch_approve/
        {
            "record_ids": [1, 2, 3],
            "action": "APPROVE",
            "notes": "Batch approved"
        }
        """
        record_ids = request.data.get('record_ids', [])
        action = request.data.get('action', 'APPROVE')
        notes = request.data.get('notes', '')
        
        records = EmissionRecord.objects.filter(id__in=record_ids)
        
        status_map = {
            'APPROVE': 'APPROVED',
            'REJECT': 'REJECTED',
            'FLAG': 'FLAGGED',
        }
        
        updated = 0
        for record in records:
            old_status = record.review_status
            record.review_status = status_map.get(action, 'PENDING')
            
            if action == 'APPROVE':
                record.approved_by = request.user
                record.approved_at = datetime.now()
            
            record.save()
            
            ReviewHistory.objects.create(
                emission_record=record,
                action=action,
                performed_by=request.user,
                notes=notes,
                changes={'review_status': old_status}
            )
            updated += 1
        
        return Response({
            'message': f'Updated {updated} records',
            'count': updated
        }, status=status.HTTP_200_OK)


class DataSourceViewSet(viewsets.ModelViewSet):
    """
    Manage data source uploads.
    
    POST /api/data-sources/ - create upload
    GET /api/data-sources/ - list
    GET /api/data-sources/{id}/ - detail
    """
    
    permission_classes = [AllowAny]  # Allow unauthenticated access in development
    serializer_class = DataSourceSerializer
    
    def get_queryset(self):
        org = Organization.objects.first()
        return DataSource.objects.filter(organization=org)
    
    def perform_create(self, serializer):
        org = Organization.objects.first()
        serializer.save(organization=org, uploaded_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """
        Process an uploaded file.
        
        POST /api/data-sources/{id}/process/
        Expects multipart form with 'file' field
        """
        data_source = self.get_object()
        
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_file = request.FILES['file']
        
        # Save temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            for chunk in uploaded_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        
        # Parse based on source type
        try:
            records = self._parse_file(tmp_path, data_source.source_type)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Normalize and create records
        normalizer = Normalizer()
        emission_records = []
        raw_records = []
        failed = 0
        
        for parsed in records:
            try:
                # Create raw record
                raw = RawRecord.objects.create(
                    data_source=data_source,
                    raw_json=parsed,
                    processing_status='NORMALIZED'
                )
                raw_records.append(raw)
                
                # Normalize
                if data_source.source_type == 'SAP':
                    normalized = normalizer.normalize_sap_record(parsed)
                elif data_source.source_type == 'UTILITY':
                    normalized = normalizer.normalize_utility_record(parsed)
                elif data_source.source_type == 'TRAVEL':
                    normalized = normalizer.normalize_travel_record(parsed)
                else:
                    normalized = {}
                
                # Create emission record
                emission = EmissionRecord.objects.create(
                    organization=data_source.organization,
                    raw_record=raw,
                    data_source=data_source,
                    scope=normalized.get('scope'),
                    category=normalized.get('category'),
                    activity_date=normalized.get('activity_date'),
                    normalized_value=normalized.get('normalized_value'),
                    normalized_unit=normalized.get('normalized_unit'),
                    original_unit=normalized.get('original_unit'),
                    emission_factor=normalized.get('emission_factor'),
                    calculated_emissions=normalized.get('calculated_emissions'),
                    confidence_score=normalized.get('confidence_score', 1.0),
                    suspicious_flags=normalized.get('suspicious_flags', {}),
                    review_status='FLAGGED' if normalized.get('suspicious_flags') else 'PENDING',
                )
                emission_records.append(emission)
            
            except Exception as e:
                failed += 1
                raw = RawRecord.objects.create(
                    data_source=data_source,
                    raw_json=parsed,
                    processing_status='FAILED',
                    error_message=str(e)
                )
        
        # Update data source
        data_source.total_rows = len(records)
        data_source.successful_rows = len(emission_records)
        data_source.failed_rows = failed
        data_source.is_processed = True
        data_source.save()
        
        return Response({
            'message': 'File processed successfully',
            'total_rows': data_source.total_rows,
            'successful_rows': data_source.successful_rows,
            'failed_rows': data_source.failed_rows,
            'emission_records': EmissionRecordListSerializer(
                emission_records, many=True
            ).data
        }, status=status.HTTP_200_OK)
    
    def _parse_file(self, file_path, source_type):
        """Route to appropriate parser"""
        if source_type == 'SAP':
            parser = SAPParser()
        elif source_type == 'UTILITY':
            parser = UtilityParser()
        elif source_type == 'TRAVEL':
            parser = TravelParser()
        else:
            raise ValueError(f"Unknown source type: {source_type}")
        
        return parser.parse(file_path)


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    """List organizations (admin only)"""
    permission_classes = [AllowAny]  # Allow unauthenticated access in development
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()