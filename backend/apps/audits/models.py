from django.db import models
from django.contrib.auth.models import User
from apps.emissions.models import Organization, EmissionRecord


class AuditLog(models.Model):
    """Complete audit trail of all actions"""
    
    ACTION_TYPES = (
        ('UPLOAD', 'File Uploaded'),
        ('PROCESS', 'File Processed'),
        ('APPROVE', 'Record Approved'),
        ('REJECT', 'Record Rejected'),
        ('FLAG', 'Record Flagged'),
        ('EDIT', 'Record Edited'),
        ('DELETE', 'Record Deleted'),
        ('EXPORT', 'Data Exported'),
    )
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    emission_record = models.ForeignKey(
        EmissionRecord, on_delete=models.SET_NULL, null=True, blank=True
    )
    
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    performed_at = models.DateTimeField(auto_now_add=True)
    
    # What changed
    changes = models.JSONField(default=dict)
    reason = models.TextField(blank=True)
    
    # IP address for security
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['organization', 'action']),
            models.Index(fields=['performed_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} by {self.performed_by} on {self.performed_at.date()}"


class ApprovalChain(models.Model):
    """Track approval chain for records"""
    
    emission_record = models.OneToOneField(
        EmissionRecord, on_delete=models.CASCADE, related_name='approval_chain'
    )
    
    # First approval
    first_approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='first_approvals'
    )
    first_approved_at = models.DateTimeField(null=True, blank=True)
    
    # Second approval (if required)
    second_approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='second_approvals'
    )
    second_approved_at = models.DateTimeField(null=True, blank=True)
    
    # Final lock for audit
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_locks'
    )
    
    class Meta:
        verbose_name = 'Approval Chain'
        verbose_name_plural = 'Approval Chains'
    
    def __str__(self):
        return f"Approval Chain for Record {self.emission_record.id}"