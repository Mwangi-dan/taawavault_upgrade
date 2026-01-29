"""
Signal handlers for core models.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
import hashlib
from core.models import (
    Group, Membership, LedgerEntry, DebitEntry, CreditEntry,
    BalanceCache, TransactionHash, EventStore, AuditLog
)


@receiver(post_save, sender=Group)
def create_balance_cache(sender, instance, created, **kwargs):
    """Create BalanceCache when Group is created."""
    if created:
        BalanceCache.objects.get_or_create(
            group=instance,
            defaults={'balance': instance.balance_cache}
        )


@receiver(post_save, sender=LedgerEntry)
def process_ledger_entry(sender, instance, created, **kwargs):
    """Process ledger entry: update balance, create hash, append event."""
    if created:
        with transaction.atomic():
            # Update balance cache
            update_balance_cache(instance)
            
            # Create transaction hash
            create_transaction_hash(instance)
            
            # Append to event store
            append_financial_event(instance)


def update_balance_cache(ledger_entry):
    """Update group balance cache."""
    group = ledger_entry.group
    balance_cache, _ = BalanceCache.objects.get_or_create(group=group)
    
    # Update balance based on entry type
    if ledger_entry.entry_type == 'EXPENSE':
        balance_cache.balance -= ledger_entry.amount
    else:
        balance_cache.balance += ledger_entry.amount
    
    balance_cache.version += 1
    balance_cache.save()
    
    # Update group balance_cache field
    group.balance_cache = balance_cache.balance
    group.version += 1
    group.save(update_fields=['balance_cache', 'version'])


def create_transaction_hash(ledger_entry):
    """Create cryptographic hash for transaction."""
    # Get previous transaction hash
    prev_hash = None
    prev_entry = LedgerEntry.objects.filter(
        group=ledger_entry.group
    ).exclude(id=ledger_entry.id).order_by('-created_at').first()
    
    if prev_entry and hasattr(prev_entry, 'transaction_hash'):
        prev_hash = prev_entry.transaction_hash.hash_value
    
    # Calculate hash
    hash_data = f"{ledger_entry.id}:{ledger_entry.amount}:{ledger_entry.description}:{ledger_entry.created_at.isoformat()}"
    if prev_hash:
        hash_data = f"{hash_data}:{prev_hash}"
    
    hash_value = hashlib.sha256(hash_data.encode()).hexdigest()
    
    # Create TransactionHash
    TransactionHash.objects.create(
        ledger_entry=ledger_entry,
        hash_value=hash_value,
        hash_prev_tx=prev_hash
    )
    
    # Update ledger entry hash_prev_tx
    ledger_entry.hash_prev_tx = prev_hash
    ledger_entry.save(update_fields=['hash_prev_tx'])


def append_financial_event(ledger_entry):
    """Append financial event to event store."""
    # Get previous event
    prev_event = EventStore.objects.filter(
        aggregate_id=ledger_entry.group_id,
        aggregate_type='Group'
    ).order_by('-event_version').first()
    
    prev_hash = prev_event.event_hash if prev_event else None
    next_version = (prev_event.event_version + 1) if prev_event else 1
    
    # Prepare event data
    event_data = {
        'ledger_entry_id': ledger_entry.id,
        'entry_type': ledger_entry.entry_type,
        'amount': str(ledger_entry.amount),
        'description': ledger_entry.description,
        'member_id': ledger_entry.member_id,
        'transaction_id': str(ledger_entry.transaction_id),
    }
    
    # Calculate event hash
    hash_data = f"{ledger_entry.group_id}:Group:{next_version}:{ledger_entry.entry_type}:{str(ledger_entry.amount)}"
    if prev_hash:
        hash_data = f"{hash_data}:{prev_hash}"
    
    event_hash = hashlib.sha256(hash_data.encode()).hexdigest()
    
    # Create event
    EventStore.objects.create(
        event_type='FINANCIAL_EVENT',
        aggregate_id=ledger_entry.group_id,
        aggregate_type='Group',
        event_data=event_data,
        event_version=next_version,
        created_by=ledger_entry.created_by,
        event_hash=event_hash,
        hash_prev_event=prev_hash
    )


@receiver(post_save, sender=Membership)
def handle_membership_event(sender, instance, created, **kwargs):
    """Append membership event to event store."""
    if created:
        # Get previous event
        prev_event = EventStore.objects.filter(
            aggregate_id=instance.group_id,
            aggregate_type='Group'
        ).order_by('-event_version').first()
        
        prev_hash = prev_event.event_hash if prev_event else None
        next_version = (prev_event.event_version + 1) if prev_event else 1
        
        # Prepare event data
        event_data = {
            'membership_id': instance.id,
            'user_id': instance.user_id,
            'role': instance.role,
            'action': 'ADD',
        }
        
        # Calculate event hash
        hash_data = f"{instance.group_id}:Group:{next_version}:MEMBERSHIP_EVENT:ADD:{instance.user_id}"
        if prev_hash:
            hash_data = f"{hash_data}:{prev_hash}"
        
        event_hash = hashlib.sha256(hash_data.encode()).hexdigest()
        
        # Create event
        EventStore.objects.create(
            event_type='MEMBERSHIP_EVENT',
            aggregate_id=instance.group_id,
            aggregate_type='Group',
            event_data=event_data,
            event_version=next_version,
            created_by=instance.user,
            event_hash=event_hash,
            hash_prev_event=prev_hash
        )


@receiver(pre_save, sender=AuditLog)
def calculate_audit_hash(sender, instance, **kwargs):
    """Calculate cryptographic hash for audit log."""
    if not instance.event_hash:
        hash_data = (
            f"{instance.event_type}:{instance.model_name}:{instance.object_id}:"
            f"{instance.user_id if instance.user_id else 'None'}:"
            f"{instance.timestamp.isoformat() if instance.timestamp else timezone.now().isoformat()}"
        )
        instance.event_hash = hashlib.sha256(hash_data.encode()).hexdigest()
