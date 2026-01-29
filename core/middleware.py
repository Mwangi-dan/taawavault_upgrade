"""
Middleware for RLS context and group access control.
"""
import re

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.db import connection
from django.contrib.auth.models import AnonymousUser
from core.models import Membership


class GroupAccessMiddleware:
    """
    Middleware to set RLS context and validate group access.
    Sets PostgreSQL session variables for Row-Level Security.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Pattern to extract group_id from URL
        self.group_pattern = re.compile(r'/groups/(\d+)/|/api/v1/groups/(\d+)/|group_id=(\d+)')
    
    def __call__(self, request):
        # Extract group_id from URL
        group_id = self.extract_group_id(request.path) or self.extract_group_id_from_query(request.GET)
        
        if group_id and request.user.is_authenticated:
            # Verify user has access to this group
            if not self.user_has_access(request.user, group_id):
                raise PermissionDenied("You do not have access to this group.")
            
            # Set RLS context in database session
            self.set_rls_context(request.user, group_id)
        
        response = self.get_response(request)
        return response
    
    def extract_group_id(self, path):
        """Extract group_id from URL path."""
        match = self.group_pattern.search(path)
        if match:
            return int(match.group(1) or match.group(2) or match.group(3))
        return None
    
    def extract_group_id_from_query(self, query_params):
        """Extract group_id from query parameters."""
        group_id = query_params.get('group_id')
        if group_id:
            try:
                return int(group_id)
            except (ValueError, TypeError):
                return None
        return None
    
    def user_has_access(self, user, group_id):
        """Check if user has access to group."""
        if user.is_superuser:
            return True
        
        return Membership.objects.filter(
            user=user,
            group_id=group_id,
            deleted_at__isnull=True
        ).exists()
    
    def set_rls_context(self, user, group_id):
        """Set PostgreSQL session variables for RLS."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SET app.current_user_id = %s",
                [user.id if not isinstance(user, AnonymousUser) else None]
            )
            cursor.execute(
                "SET app.current_group_id = %s",
                [group_id]
            )
            cursor.execute(
                "SET app.is_superuser = %s",
                [user.is_superuser if not isinstance(user, AnonymousUser) else False]
            )
            if user.is_superuser:
                cursor.execute("SET app.audit_superuser_access = TRUE")


class AuditLoggingMiddleware:
    """
    Middleware to log requests for audit purposes.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip logging for static files and common paths
        if self.should_skip_logging(request.path):
            return self.get_response(request)
        
        # Get client IP
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Log view access for authenticated users
        if request.user.is_authenticated and request.method == 'GET':
            from core.models import AuditLog
            AuditLog.objects.create(
                event_type='VIEW',
                model_name='Page',
                object_id=0,
                user=request.user,
                ip_address=ip_address,
                user_agent=user_agent,
                after_value={'path': request.path, 'method': request.method}
            )
        
        response = self.get_response(request)
        return response
    
    def should_skip_logging(self, path):
        """Determine if logging should be skipped for this path."""
        skip_patterns = [
            '/static/',
            '/media/',
            '/admin/jsi18n/',
            '/favicon.ico',
            '/health/',
            '/api/v1/token/',
        ]
        return any(path.startswith(pattern) for pattern in skip_patterns)
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
