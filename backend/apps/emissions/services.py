from django.db.models import Sum, Count, Q
from decimal import Decimal
from apps.emissions.models import EmissionRecord, ReviewHistory


class EmissionService:
    """Business logic for emissions"""
    
    @staticmethod
    def get_dashboard_stats(organization):
        """Get dashboard metrics"""
        queryset = EmissionRecord.objects.filter(organization=organization)
        
        total_emissions = queryset.aggregate(
            total=Sum('calculated_emissions')
        )['total'] or Decimal('0')
        
        emissions_by_scope = {}
        for scope in ['SCOPE_1', 'SCOPE_2', 'SCOPE_3']:
            total = queryset.filter(scope=scope).aggregate(
                total=Sum('calculated_emissions')
            )['total'] or Decimal('0')
            emissions_by_scope[scope] = float(total)
        
        return {
            'total_records': queryset.count(),
            'pending_review': queryset.filter(review_status='PENDING').count(),
            'flagged': queryset.filter(review_status='FLAGGED').count(),
            'approved': queryset.filter(review_status='APPROVED').count(),
            'rejected': queryset.filter(review_status='REJECTED').count(),
            'total_emissions': float(total_emissions),
            'emissions_by_scope': emissions_by_scope,
        }
    
    @staticmethod
    def approve_record(emission_record, user, notes=''):
        """Approve an emission record"""
        old_status = emission_record.review_status
        emission_record.review_status = 'APPROVED'
        emission_record.approved_by = user
        emission_record.approved_at = None  # Will be set by model
        emission_record.review_notes = notes
        emission_record.save()
        
        ReviewHistory.objects.create(
            emission_record=emission_record,
            action='APPROVED',
            performed_by=user,
            notes=notes,
            changes={'review_status': f'{old_status} → APPROVED'}
        )
    
    @staticmethod
    def reject_record(emission_record, user, notes=''):
        """Reject an emission record"""
        old_status = emission_record.review_status
        emission_record.review_status = 'REJECTED'
        emission_record.review_notes = notes
        emission_record.save()
        
        ReviewHistory.objects.create(
            emission_record=emission_record,
            action='REJECTED',
            performed_by=user,
            notes=notes,
            changes={'review_status': f'{old_status} → REJECTED'}
        )
    
    @staticmethod
    def flag_record(emission_record, user, notes=''):
        """Flag a record as suspicious"""
        old_status = emission_record.review_status
        emission_record.review_status = 'FLAGGED'
        emission_record.review_notes = notes
        emission_record.save()
        
        ReviewHistory.objects.create(
            emission_record=emission_record,
            action='FLAGGED',
            performed_by=user,
            notes=notes,
            changes={'review_status': f'{old_status} → FLAGGED'}
        )
    
    @staticmethod
    def batch_approve(record_ids, user, notes=''):
        """Approve multiple records"""
        records = EmissionRecord.objects.filter(id__in=record_ids)
        
        for record in records:
            EmissionService.approve_record(record, user, notes)
        
        return records.count()