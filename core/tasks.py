"""
Celery tasks for async operations.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


@shared_task
def send_email_notification(user_id, message, notification_type):
    """Send email notification."""
    from django.contrib.auth.models import User
    user = User.objects.get(id=user_id)
    
    subject = f"TaawaVault Notification: {notification_type}"
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@shared_task
def send_whatsapp_notification(user_id, message):
    """Send WhatsApp notification (placeholder)."""
    # TODO: Implement WhatsApp API integration
    pass


@shared_task(bind=True, max_retries=3)
def generate_pdf_report_async(self, group_id, user_id):
    """Generate PDF report asynchronously."""
    try:
        from core.models import Group, LedgerEntry
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        import io
        
        group = Group.objects.get(id=group_id)
        entries = LedgerEntry.objects.filter(group=group).order_by('-occurred_at')[:100]
        
        # Generate PDF (simplified - full implementation would be more complex)
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        story.append(Paragraph(f"Group Report: {group.name}", styles['Title']))
        story.append(Paragraph(f"Balance: {group.balance_cache} {group.currency}", styles['Normal']))
        
        # Table data
        data = [['Date', 'Type', 'Amount', 'Description']]
        for entry in entries:
            data.append([
                entry.occurred_at.strftime('%Y-%m-%d'),
                entry.entry_type,
                str(entry.amount),
                entry.description[:50],
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), '#4472C4'),
            ('TEXTCOLOR', (0, 0), (-1, 0), '#FFFFFF'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), '#F2F2F2'),
            ('GRID', (0, 0), (-1, -1), 1, '#CCCCCC'),
        ]))
        
        story.append(table)
        doc.build(story)
        
        # TODO: Upload to S3 and notify user
        # For now, just return success
        return f"Report generated for group {group_id}"
        
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
