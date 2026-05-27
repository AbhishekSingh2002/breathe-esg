from django.db import models
from django.contrib.auth.models import User
from apps.emissions.models import Organization, DataSource


class FileUpload(models.Model):
    """
    High-level view of a file upload.
    Links to DataSource and RawRecords.
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    source_type = models.CharField(
        max_length=20,
        choices=[
            ('SAP', 'SAP'),
            ('UTILITY', 'Utility'),
            ('TRAVEL', 'Travel'),
        ]
    )
    
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()  # bytes
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Counts
    total_rows = models.IntegerField(default=0)
    successful_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.file_name} ({self.source_type})"
