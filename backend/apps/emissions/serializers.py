from rest_framework import serializers
from apps.emissions.models import (
    Organization, DataSource, RawRecord, EmissionRecord, ReviewHistory
)
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'created_at', 'updated_at']


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = [
            'id', 'source_type', 'uploaded_by', 'uploaded_at',
            'raw_file_name', 'raw_file_size',
            'total_rows', 'successful_rows', 'failed_rows',
            'is_processed'
        ]
        read_only_fields = [
            'total_rows', 'successful_rows', 'failed_rows', 'is_processed'
        ]


class RawRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRecord
        fields = [
            'id', 'raw_json', 'processing_status',
            'error_message', 'created_at', 'processed_at'
        ]
        read_only_fields = [
            'processing_status', 'error_message', 'created_at', 'processed_at'
        ]


class ReviewHistorySerializer(serializers.ModelSerializer):
    performed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = ReviewHistory
        fields = [
            'id', 'action', 'performed_by', 'performed_at',
            'notes', 'changes'
        ]
        read_only_fields = [
            'performed_by', 'performed_at', 'action'
        ]


class EmissionRecordListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    approved_by = UserSerializer(read_only=True)
    data_source = DataSourceSerializer(read_only=True)
    
    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'scope', 'category', 'activity_date',
            'normalized_value', 'normalized_unit',
            'calculated_emissions',
            'confidence_score', 'review_status',
            'approved_by', 'approved_at',
            'data_source'
        ]
        read_only_fields = [
            'normalized_value', 'normalized_unit',
            'calculated_emissions', 'confidence_score'
        ]


class EmissionRecordDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail views"""
    approved_by = UserSerializer(read_only=True)
    raw_record = RawRecordSerializer(read_only=True)
    data_source = DataSourceSerializer(read_only=True)
    review_history = ReviewHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'organization', 'scope', 'category', 'activity_date',
            'normalized_value', 'normalized_unit', 'original_unit',
            'emission_factor', 'calculated_emissions',
            'confidence_score', 'suspicious_flags',
            'review_status', 'review_notes',
            'approved_by', 'approved_at',
            'created_at', 'updated_at',
            'raw_record', 'data_source', 'review_history'
        ]
        read_only_fields = [
            'normalized_value', 'normalized_unit',
            'emission_factor', 'calculated_emissions',
            'confidence_score', 'suspicious_flags',
            'created_at', 'updated_at'
        ]


class EmissionRecordApproveSerializer(serializers.Serializer):
    """For approval/rejection actions"""
    action = serializers.ChoiceField(
        choices=['APPROVE', 'REJECT', 'FLAG'],
        help_text="APPROVE: lock for audit, REJECT: send back, FLAG: mark suspicious"
    )
    notes = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Why are you approving/rejecting?"
    )


class DashboardStatsSerializer(serializers.Serializer):
    """Dashboard metrics"""
    total_records = serializers.IntegerField()
    pending_review = serializers.IntegerField()
    flagged_suspicious = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    
    total_emissions = serializers.DecimalField(
        max_digits=15, decimal_places=4,
        help_text="Total calculated kg CO2e"
    )
    
    emissions_by_scope = serializers.DictField(
        child=serializers.DecimalField(max_digits=15, decimal_places=4),
        help_text="Emissions breakdown by Scope 1/2/3"
    )