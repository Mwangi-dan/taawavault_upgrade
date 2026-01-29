"""
Custom decorators for permission checks.
"""
from functools import wraps
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import Group, Membership


def group_required(view_func):
    """
    Decorator to ensure user has access to the group.
    """
    @wraps(view_func)
    def _wrapped_view(request, group_id, *args, **kwargs):
        group = get_object_or_404(Group, id=group_id)
        
        # Superusers have access
        if request.user.is_superuser:
            return view_func(request, group_id, *args, **kwargs)
        
        # Check membership
        membership = Membership.objects.filter(
            user=request.user,
            group=group,
            deleted_at__isnull=True
        ).first()
        
        if not membership:
            raise PermissionDenied("You do not have access to this group.")
        
        return view_func(request, group_id, *args, **kwargs)
    
    return _wrapped_view


def admin_or_treasurer_required(view_func):
    """
    Decorator to ensure user is admin or treasurer.
    """
    @wraps(view_func)
    @group_required
    def _wrapped_view(request, group_id, *args, **kwargs):
        group = get_object_or_404(Group, id=group_id)
        
        # Superusers have access
        if request.user.is_superuser:
            return view_func(request, group_id, *args, **kwargs)
        
        # Check role
        membership = Membership.objects.filter(
            user=request.user,
            group=group,
            deleted_at__isnull=True
        ).first()
        
        if not membership or membership.role not in ['ADMIN', 'TREASURER']:
            raise PermissionDenied("You must be an administrator or treasurer to perform this action.")
        
        return view_func(request, group_id, *args, **kwargs)
    
    return _wrapped_view


def admin_required(view_func):
    """
    Decorator to ensure user is admin.
    """
    @wraps(view_func)
    @group_required
    def _wrapped_view(request, group_id, *args, **kwargs):
        group = get_object_or_404(Group, id=group_id)
        
        # Superusers have access
        if request.user.is_superuser:
            return view_func(request, group_id, *args, **kwargs)
        
        # Check role
        membership = Membership.objects.filter(
            user=request.user,
            group=group,
            deleted_at__isnull=True
        ).first()
        
        if not membership or membership.role != 'ADMIN':
            raise PermissionDenied("You must be an administrator to perform this action.")
        
        return view_func(request, group_id, *args, **kwargs)
    
    return _wrapped_view
