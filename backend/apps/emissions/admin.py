from django.contrib import admin
from apps.emissions.models import (
    Organization, DataSource, RawRecord, EmissionRecord, ReviewHistory
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('source_type', 'uploaded_by', 'uploaded_at', 'total_rows', 'successful_rows', 'failed_rows', 'is_processed')
    list_filter = ('source_type', 'is_processed', 'uploaded_at')
    search_fields = ('raw_file_name',)
    readonly_fields = ('uploaded_at', 'total_rows', 'successful_rows', 'failed_rows')
    
    fieldsets = (
        ('Source Info', {
            'fields': ('organization', 'source_type', 'uploaded_by', 'uploaded_at')
        }),
        ('File Details', {
            'fields': ('raw_file_name', 'raw_file_size')
        }),
        ('Processing', {
            'fields': ('total_rows', 'successful_rows', 'failed_rows', 'is_processed')
        }),
    )


@admin.register(RawRecord)
class RawRecordAdmin(admin.ModelAdmin):
    list_display = ('data_source', 'processing_status', 'created_at')
    list_filter = ('processing_status', 'data_source__source_type')
    search_fields = ('data_source__raw_file_name',)
    readonly_fields = ('created_at', 'processed_at', 'raw_json')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('data_source')


@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ('activity_date', 'category', 'scope', 'calculated_emissions', 'confidence_score', 'review_status', 'approved_by')
    list_filter = ('scope', 'category', 'review_status', 'activity_date')
    search_fields = ('raw_record__raw_json', 'approved_by__username')
    readonly_fields = ('calculated_emissions', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('organization', 'activity_date', 'scope', 'category')
        }),
        ('Activity Data', {
            'fields': ('normalized_value', 'normalized_unit', 'original_unit')
        }),
        ('Emissions', {
            'fields': ('emission_factor', 'calculated_emissions')
        }),
        ('Data Quality', {
            'fields': ('confidence_score', 'suspicious_flags')
        }),
        ('Review', {
            'fields': ('review_status', 'review_notes', 'approved_by', 'approved_at')
        }),
        ('Audit', {
            'fields': ('raw_record', 'data_source', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('approved_by', 'raw_record', 'data_source')


@admin.register(ReviewHistory)
class ReviewHistoryAdmin(admin.ModelAdmin):
    list_display = ('emission_record', 'action', 'performed_by', 'performed_at')
    list_filter = ('action', 'performed_at')
    search_fields = ('performed_by__username', 'notes')
    readonly_fields = ('performed_at', 'performed_by')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('performed_by', 'emission_record')
