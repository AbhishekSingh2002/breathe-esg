from django.db import models
from django.contrib.auth.models import User
import json

# ============================================================================
# ORGANIZATION & SOURCE TRACKING
# ============================================================================

class Organization(models.Model):
    """
    Multi-tenant root. Each client is an Organization.
    """
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


class DataSource(models.Model):
    """
    Tracks WHERE a row came from.
    
    Critical for audit trail:
    - Which file was uploaded?
    - When?
    - By whom?
    - What was the original state?
    """
    SOURCE_TYPES = (
        ('SAP', 'SAP Fuel & Procurement'),
        ('UTILITY', 'Utility Electricity Data'),
        ('TRAVEL', 'Corporate Travel'),
    )
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # The raw file data - preserve it
    raw_file_name = models.CharField(max_length=255)
    raw_file_size = models.IntegerField()  # bytes
    
    # Processing metadata
    total_rows = models.IntegerField(default=0)
    successful_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    
    is_processed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.get_source_type_display()} - {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"


# ============================================================================
# RAW RECORDS - NEVER DELETE THESE
# ============================================================================

class RawRecord(models.Model):
    """
    CRITICAL: Store the raw imported row EXACTLY as received.
    
    Auditors will ask: "Where did this number come from?"
    Answer: From this RawRecord.
    
    This is what separates a serious system from toy projects.
    """
    PROCESSING_STATUS = (
        ('PENDING', 'Pending Normalization'),
        ('NORMALIZED', 'Successfully Normalized'),
        ('FAILED', 'Normalization Failed'),
        ('APPROVED', 'Approved for Audit'),
        ('REJECTED', 'Rejected by Analyst'),
    )
    
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='raw_records')
    
    # The raw row, preserved exactly
    raw_json = models.JSONField()
    
    # Processing state
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS, default='PENDING')
    error_message = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['data_source', '-created_at']
        indexes = [
            models.Index(fields=['data_source', 'processing_status']),
        ]
    
    def __str__(self):
        return f"Raw {self.data_source.source_type} - {self.get_processing_status_display()}"


# ============================================================================
# EMISSION RECORDS - THE MAIN WORKING TABLE
# ============================================================================

class EmissionRecord(models.Model):
    """
    The normalized, analyst-friendly table.
    
    This is where all business logic lives.
    Each row represents ONE normalized piece of emissions data.
    """
    SCOPE_CHOICES = (
        ('SCOPE_1', 'Scope 1 - Direct'),
        ('SCOPE_2', 'Scope 2 - Indirect (Energy)'),
        ('SCOPE_3', 'Scope 3 - Indirect (Other)'),
    )
    
    CATEGORY_CHOICES = (
        ('FUEL_DIESEL', 'Fuel - Diesel'),
        ('FUEL_PETROL', 'Fuel - Petrol'),
        ('FUEL_LPG', 'Fuel - LPG'),
        ('FUEL_CNG', 'Fuel - CNG'),
        ('ELECTRICITY', 'Electricity'),
        ('TRAVEL_FLIGHT', 'Travel - Flight'),
        ('TRAVEL_HOTEL', 'Travel - Hotel'),
        ('TRAVEL_GROUND', 'Travel - Ground Transport'),
    )
    
    REVIEW_STATUS = (
        ('PENDING', 'Pending Review'),
        ('FLAGGED', 'Flagged - Suspicious'),
        ('APPROVED', 'Approved for Audit'),
        ('REJECTED', 'Rejected'),
    )
    
    # ========== Organization & Source ==========
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='emission_records')
    raw_record = models.OneToOneField(RawRecord, on_delete=models.CASCADE, related_name='emission_record')
    data_source = models.ForeignKey(DataSource, on_delete=models.PROTECT)
    
    # ========== Classification ==========
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    
    # ========== Activity Data (Normalized) ==========
    activity_date = models.DateField(help_text="When did this activity occur?")
    
    # The actual value, normalized to canonical units
    normalized_value = models.DecimalField(max_digits=15, decimal_places=4)
    normalized_unit = models.CharField(max_length=20, help_text="kWh, kg, km, etc.")
    
    # Source unit (for reference)
    original_unit = models.CharField(max_length=20, null=True, blank=True)
    
    # ========== Emissions Calculation ==========
    emission_factor = models.DecimalField(max_digits=10, decimal_places=6, help_text="kg CO2e per unit")
    calculated_emissions = models.DecimalField(max_digits=15, decimal_places=4, help_text="kg CO2e")
    
    # ========== Data Quality ==========
    confidence_score = models.FloatField(
        default=1.0, 
        help_text="0.0-1.0. How confident are we in this data?"
    )
    
    suspicious_flags = models.JSONField(default=dict, blank=True, help_text="Why was this flagged?")
    
    # ========== Review Workflow ==========
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS, default='PENDING')
    review_notes = models.TextField(null=True, blank=True)
    
    # ========== Approval ==========
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # ========== Metadata ==========
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-activity_date', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'scope', 'review_status']),
            models.Index(fields=['organization', 'activity_date']),
            models.Index(fields=['review_status']),
        ]
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.activity_date} ({self.get_review_status_display()})"


# ============================================================================
# AUDIT TRAIL - COMPLETE HISTORY
# ============================================================================

class ReviewHistory(models.Model):
    """
    Every action on an EmissionRecord is logged here.
    
    Auditors love this. Shows:
    - Who did what
    - When
    - Why
    """
    ACTION_TYPES = (
        ('CREATED', 'Record Created'),
        ('FLAGGED', 'Flagged Suspicious'),
        ('UNFLAGGED', 'Unflagged'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('EDITED', 'Edited'),
    )
    
    emission_record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name='review_history')
    
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    performed_at = models.DateTimeField(auto_now_add=True)
    
    notes = models.TextField(null=True, blank=True)
    
    # What changed?
    changes = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-performed_at']
    
    def __str__(self):
        return f"{self.get_action_display()} by {self.performed_by} on {self.performed_at.date()}"