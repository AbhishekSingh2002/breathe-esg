from datetime import datetime
from django.db import transaction
from .models import AuditLog, ApprovalChain
from apps.emissions.models import EmissionRecord


class AuditService:
    """Handle audit trail and compliance"""
    
    @staticmethod
    def log_action(organization, action, user, emission_record=None, 
                   changes=None, reason='', ip_address=None):
        """Log an action to audit trail"""
        AuditLog.objects.create(
            organization=organization,
            action=action,
            performed_by=user,
            emission_record=emission_record,
            changes=changes or {},
            reason=reason,
            ip_address=ip_address
        )
    
    @staticmethod
    def get_audit_trail(organization, filters=None):
        """Get audit trail for organization"""
        logs = AuditLog.objects.filter(organization=organization)
        
        if filters:
            if 'action' in filters:
                logs = logs.filter(action=filters['action'])
            if 'user' in filters:
                logs = logs.filter(performed_by=filters['user'])
            if 'start_date' in filters:
                logs = logs.filter(performed_at__gte=filters['start_date'])
            if 'end_date' in filters:
                logs = logs.filter(performed_at__lte=filters['end_date'])
        
        return logs.order_by('-performed_at')
    
    @staticmethod
    @transaction.atomic
    def approve_for_audit(emission_record, user):
        """Lock record for audit - final approval"""
        
        # Get or create approval chain
        approval_chain, created = ApprovalChain.objects.get_or_create(
            emission_record=emission_record
        )
        
        # Check if first approval exists
        if not approval_chain.first_approved_by:
            approval_chain.first_approved_by = user
            approval_chain.first_approved_at = datetime.now()
        else:
            # Second approval
            approval_chain.second_approved_by = user
            approval_chain.second_approved_at = datetime.now()
            approval_chain.locked_at = datetime.now()
            approval_chain.locked_by = user
        
        approval_chain.save()
        
        # Update emission record
        emission_record.review_status = 'APPROVED'
        emission_record.approved_by = user
        emission_record.save()
        
        # Log action
        AuditService.log_action(
            emission_record.organization,
            'APPROVE',
            user,
            emission_record,
            {'review_status': 'APPROVED'},
            'Approved for audit'
        )
        
        return approval_chain
    
    @staticmethod
    def get_approval_status(emission_record):
        """Check approval status"""
        try:
            chain = ApprovalChain.objects.get(emission_record=emission_record)
            return {
                'first_approved': chain.first_approved_by is not None,
                'first_approved_by': chain.first_approved_by.username if chain.first_approved_by else None,
                'second_approved': chain.second_approved_by is not None,
                'second_approved_by': chain.second_approved_by.username if chain.second_approved_by else None,
                'locked': chain.locked_at is not None,
                'locked_by': chain.locked_by.username if chain.locked_by else None,
            }
        except ApprovalChain.DoesNotExist:
            return {
                'first_approved': False,
                'second_approved': False,
                'locked': False,
            }
    
    @staticmethod
    def generate_audit_report(organization, start_date, end_date):
        """Generate audit report"""
        logs = AuditLog.objects.filter(
            organization=organization,
            performed_at__gte=start_date,
            performed_at__lte=end_date
        ).order_by('performed_at')
        
        report = {
            'organization': organization.name,
            'period': f'{start_date.date()} to {end_date.date()}',
            'total_actions': logs.count(),
            'by_action': {},
            'by_user': {},
            'actions': []
        }
        
        # Count by action
        for log in logs:
            action = log.get_action_display()
            report['by_action'][action] = report['by_action'].get(action, 0) + 1
            
            user = log.performed_by.username if log.performed_by else 'Unknown'
            report['by_user'][user] = report['by_user'].get(user, 0) + 1
            
            report['actions'].append({
                'timestamp': log.performed_at.isoformat(),
                'action': action,
                'user': user,
                'record_id': log.emission_record.id if log.emission_record else None,
                'reason': log.reason,
            })
        
        return report