"""
Core views for TaawaVault.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import connection
from django.core.cache import cache
from .models import Group, Membership, LedgerEntry
from .decorators import group_required


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for monitoring."""
    checks = {
        'database': False,
        'redis': False,
        'status': 'unhealthy'
    }
    
    # Check database
    try:
        Group.objects.first()
        checks['database'] = True
    except:
        pass
    
    # Check Redis
    try:
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
        checks['redis'] = True
    except:
        pass
    
    # Overall status
    if checks['database'] and checks['redis']:
        checks['status'] = 'healthy'
    
    status_code = 200 if checks['status'] == 'healthy' else 503
    
    return JsonResponse(checks, status=status_code)


@login_required
def dashboard(request):
    """Main dashboard view."""
    # Get user's groups
    groups = Group.objects.filter(
        memberships__user=request.user,
        memberships__deleted_at__isnull=True
    ).distinct()
    
    # Get recent transactions across all groups
    recent_transactions = LedgerEntry.objects.filter(
        group__in=groups
    ).select_related('group', 'member__user')[:10]
    
    # Calculate total balance across all groups
    total_balance = sum(group.balance_cache for group in groups)
    
    context = {
        'groups': groups,
        'recent_transactions': recent_transactions,
        'total_balance': total_balance,
        'groups_count': groups.count(),
    }
    
    return render(request, 'core/dashboard.html', context)


@login_required
def group_list(request):
    """List all groups user belongs to."""
    groups = Group.objects.filter(
        memberships__user=request.user,
        memberships__deleted_at__isnull=True
    ).distinct().select_related()
    
    context = {
        'groups': groups,
    }
    
    return render(request, 'core/group_list.html', context)


@login_required
@group_required
def group_detail(request, group_id):
    """Group detail view."""
    group = get_object_or_404(Group, id=group_id)
    
    # Get membership
    membership = Membership.objects.filter(
        user=request.user,
        group=group,
        deleted_at__isnull=True
    ).first()
    
    # Get recent transactions
    recent_transactions = LedgerEntry.objects.filter(
        group=group
    ).select_related('member__user')[:20]
    
    # Get members
    members = Membership.objects.filter(
        group=group,
        deleted_at__isnull=True
    ).select_related('user')
    
    context = {
        'group': group,
        'membership': membership,
        'recent_transactions': recent_transactions,
        'members': members,
    }
    
    return render(request, 'core/group_detail.html', context)


@login_required
@group_required
def ledger_list(request, group_id):
    """List ledger entries for a group."""
    group = get_object_or_404(Group, id=group_id)
    
    # Get filter parameters
    entry_type = request.GET.get('entry_type', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Build query
    entries = LedgerEntry.objects.filter(group=group).select_related('member__user', 'created_by')
    
    if entry_type:
        entries = entries.filter(entry_type=entry_type)
    
    if start_date:
        entries = entries.filter(occurred_at__gte=start_date)
    
    if end_date:
        entries = entries.filter(occurred_at__lte=end_date)
    
    entries = entries.order_by('-occurred_at', '-created_at')
    
    context = {
        'group': group,
        'entries': entries,
        'entry_type': entry_type,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'core/ledger_list.html', context)


@login_required
@group_required
def member_list(request, group_id):
    """List members of a group."""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is admin
    membership = Membership.objects.filter(
        user=request.user,
        group=group,
        deleted_at__isnull=True
    ).first()
    
    is_admin = membership and membership.role == 'ADMIN'
    
    # Get members
    members = Membership.objects.filter(
        group=group,
        deleted_at__isnull=True
    ).select_related('user')
    
    context = {
        'group': group,
        'members': members,
        'is_admin': is_admin,
    }
    
    return render(request, 'core/member_list.html', context)


@login_required
@group_required
def reports(request, group_id):
    """Reports view for a group."""
    group = get_object_or_404(Group, id=group_id)
    
    # Get summary statistics
    total_contributions = LedgerEntry.objects.filter(
        group=group,
        entry_type='CONTRIBUTION'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    total_expenses = LedgerEntry.objects.filter(
        group=group,
        entry_type='EXPENSE'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'group': group,
        'total_contributions': total_contributions,
        'total_expenses': total_expenses,
        'current_balance': group.balance_cache,
    }
    
    return render(request, 'core/reports.html', context)
