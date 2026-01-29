"""
Custom managers for RLS-aware queries.
"""
from django.db import models


class GroupManager(models.Manager):
    """Manager for Group model with RLS awareness."""
    
    def for_user(self, user):
        """Get groups that user is a member of."""
        if user.is_superuser:
            return self.all()
        return self.filter(memberships__user=user, memberships__deleted_at__isnull=True).distinct()


class MembershipManager(models.Manager):
    """Manager for Membership model with RLS awareness."""
    
    def active(self):
        """Get active (non-deleted) memberships."""
        return self.filter(deleted_at__isnull=True)
    
    def for_group(self, group_id):
        """Get memberships for a specific group."""
        return self.filter(group_id=group_id, deleted_at__isnull=True)
    
    def for_user(self, user_id):
        """Get memberships for a specific user."""
        return self.filter(user_id=user_id, deleted_at__isnull=True)


class LedgerEntryManager(models.Manager):
    """Manager for LedgerEntry model with RLS awareness."""
    
    def for_group(self, group_id):
        """Get ledger entries for a specific group."""
        return self.filter(group_id=group_id)
    
    def for_member(self, member_id):
        """Get ledger entries for a specific member."""
        return self.filter(member_id=member_id)
    
    def contributions(self):
        """Get contribution entries."""
        return self.filter(entry_type='CONTRIBUTION')
    
    def expenses(self):
        """Get expense entries."""
        return self.filter(entry_type='EXPENSE')
