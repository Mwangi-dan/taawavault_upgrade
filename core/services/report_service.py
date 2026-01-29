"""
Report Generation Service for PDF and CSV exports.
"""
from django.http import HttpResponse
from django.db.models import Sum, Count
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from core.models import Group, LedgerEntry, Membership
from core.tasks import generate_pdf_report_async
import csv
import io


class ReportService:
    """Service for generating financial reports."""
    
    @staticmethod
    def generate_group_summary_pdf(group_id, user_id):
        """
        Generate group summary PDF report asynchronously.
        Returns job_id for tracking.
        """
        # Queue async task
        task = generate_pdf_report_async.delay(group_id, user_id)
        return task.id
    
    @staticmethod
    def generate_group_summary_csv(group_id):
        """Generate group summary CSV report (streaming)."""
        group = Group.objects.get(id=group_id)
        entries = LedgerEntry.objects.filter(group=group).order_by('-occurred_at')
        
        # Create streaming response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="group_{group_id}_summary.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Amount', 'Description', 'Member', 'Reference'])
        
        for entry in entries:
            writer.writerow([
                entry.occurred_at.strftime('%Y-%m-%d %H:%M:%S'),
                entry.entry_type,
                entry.amount,
                entry.description,
                entry.member.user.username if entry.member else '',
                entry.reference or '',
            ])
        
        return response
    
    @staticmethod
    def generate_contribution_report(group_id, start_date=None, end_date=None):
        """Generate contribution report."""
        group = Group.objects.get(id=group_id)
        
        entries = LedgerEntry.objects.filter(
            group=group,
            entry_type='CONTRIBUTION'
        )
        
        if start_date:
            entries = entries.filter(occurred_at__gte=start_date)
        if end_date:
            entries = entries.filter(occurred_at__lte=end_date)
        
        # Group by member
        member_contributions = {}
        for entry in entries.select_related('member__user'):
            if entry.member:
                member_id = entry.member.id
                if member_id not in member_contributions:
                    member_contributions[member_id] = {
                        'member': entry.member.user.username,
                        'total': 0,
                        'count': 0,
                    }
                member_contributions[member_id]['total'] += entry.amount
                member_contributions[member_id]['count'] += 1
        
        return {
            'group': group,
            'period': {'start': start_date, 'end': end_date},
            'member_contributions': member_contributions,
            'total_contributions': sum(c['total'] for c in member_contributions.values()),
        }
