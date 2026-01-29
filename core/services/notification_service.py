"""
Notification Service for sending notifications via multiple channels.
"""
from django.contrib.auth.models import User
from core.models import ConsentRecord
from core.tasks import send_email_notification, send_whatsapp_notification


class NotificationService:
    """Service for sending notifications."""
    
    @staticmethod
    def notify(user_id, message, notification_type, channels=None):
        """
        Send notification to user via specified channels.
        
        Args:
            user_id: User ID
            message: Notification message
            notification_type: Type of notification
            channels: List of channels ['in_app', 'email', 'whatsapp']
        """
        if channels is None:
            channels = ['in_app']
        
        user = User.objects.get(id=user_id)
        
        # Create in-app notification (if supported)
        if 'in_app' in channels:
            # TODO: Create Notification model and store
            pass
        
        # Send email
        if 'email' in channels:
            send_email_notification.delay(user_id, message, notification_type)
        
        # Send WhatsApp (with consent check)
        if 'whatsapp' in channels:
            if NotificationService.has_consent(user_id, 'WHATSAPP_NOTIFICATION'):
                send_whatsapp_notification.delay(user_id, message)
            else:
                # Log that consent is required
                pass
    
    @staticmethod
    def has_consent(user_id, purpose):
        """Check if user has granted consent for purpose."""
        return ConsentRecord.objects.filter(
            user_id=user_id,
            purpose=purpose,
            granted=True,
            revoked_at__isnull=True
        ).exists()
