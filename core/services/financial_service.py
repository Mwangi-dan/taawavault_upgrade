"""
Financial Service for double-entry accounting and transaction processing.
"""
import uuid
from decimal import Decimal
from django.db import transaction, models
from django.core.cache import cache
from django.utils import timezone
from django.core.exceptions import ValidationError
import redis
from core.models import (
    Group, Membership, LedgerEntry, DebitEntry, CreditEntry,
    BalanceCache
)


class InsufficientFundsException(Exception):
    """Raised when group has insufficient funds."""
    pass


class FinancialService:
    """Service for financial operations with double-entry accounting."""
    
    def __init__(self):
        try:
            self.redis_client = redis.Redis.from_url('redis://localhost:6379/0')
        except:
            self.redis_client = None
    
    def _acquire_lock(self, lock_key, timeout=30):
        """Acquire distributed lock."""
        if not self.redis_client:
            return None
        
        lock = self.redis_client.lock(lock_key, timeout=timeout)
        acquired = lock.acquire(blocking=True, timeout=10)
        return lock if acquired else None
    
    def _release_lock(self, lock):
        """Release distributed lock."""
        if lock:
            lock.release()
    
    @transaction.atomic
    def create_contribution(self, group_id, member_id, amount, description, 
                          created_by, transaction_id=None, reference=None):
        """
        Create a contribution transaction with double-entry accounting.
        
        Debit: CASH
        Credit: MEMBER_CONTRIBUTIONS
        """
        # Generate transaction_id if not provided
        if transaction_id is None:
            transaction_id = uuid.uuid4()
        else:
            transaction_id = uuid.UUID(str(transaction_id))
        
        # Check idempotency
        existing = LedgerEntry.objects.filter(transaction_id=transaction_id).first()
        if existing:
            return existing
        
        # Acquire distributed lock
        lock_key = f'group:{group_id}:balance'
        lock = self._acquire_lock(lock_key)
        
        try:
            # Acquire pessimistic lock
            group = Group.objects.select_for_update().get(id=group_id)
            member = Membership.objects.get(id=member_id, group_id=group_id, deleted_at__isnull=True)
            
            # Validate amount
            if amount <= 0:
                raise ValidationError("Amount must be positive.")
            
            # Create ledger entry
            ledger_entry = LedgerEntry.objects.create(
                group=group,
                member=member,
                entry_type='CONTRIBUTION',
                amount=amount,
                description=description,
                reference=reference,
                created_by=created_by,
                transaction_id=transaction_id,
            )
            
            # Create double-entry
            DebitEntry.objects.create(
                ledger_entry=ledger_entry,
                account='CASH',
                amount=amount
            )
            CreditEntry.objects.create(
                ledger_entry=ledger_entry,
                account='MEMBER_CONTRIBUTIONS',
                amount=amount
            )
            
            # Invalidate cache
            cache.delete(f'group:{group_id}:balance')
            cache.delete(f'group:{group_id}:summary')
            
            return ledger_entry
            
        finally:
            self._release_lock(lock)
    
    @transaction.atomic
    def create_expense(self, group_id, amount, description, created_by,
                      transaction_id=None, reference=None, require_approval=False):
        """
        Create an expense transaction with double-entry accounting.
        
        Debit: EXPENSES
        Credit: CASH
        """
        # Generate transaction_id if not provided
        if transaction_id is None:
            transaction_id = uuid.uuid4()
        else:
            transaction_id = uuid.UUID(str(transaction_id))
        
        # Check idempotency
        existing = LedgerEntry.objects.filter(transaction_id=transaction_id).first()
        if existing:
            return existing
        
        # Acquire distributed lock
        lock_key = f'group:{group_id}:balance'
        lock = self._acquire_lock(lock_key)
        
        try:
            # Acquire pessimistic lock
            group = Group.objects.select_for_update().get(id=group_id)
            
            # Validate balance
            if group.balance_cache < amount:
                raise InsufficientFundsException(
                    f"Insufficient funds. Current balance: {group.balance_cache}, "
                    f"Requested: {amount}"
                )
            
            # Validate amount
            if amount <= 0:
                raise ValidationError("Amount must be positive.")
            
            # Create ledger entry (negative amount for expense)
            ledger_entry = LedgerEntry.objects.create(
                group=group,
                entry_type='EXPENSE',
                amount=-amount,  # Negative for expense
                description=description,
                reference=reference,
                created_by=created_by,
                transaction_id=transaction_id,
            )
            
            # Create double-entry
            DebitEntry.objects.create(
                ledger_entry=ledger_entry,
                account='EXPENSES',
                amount=amount
            )
            CreditEntry.objects.create(
                ledger_entry=ledger_entry,
                account='CASH',
                amount=amount
            )
            
            # Invalidate cache
            cache.delete(f'group:{group_id}:balance')
            cache.delete(f'group:{group_id}:summary')
            
            return ledger_entry
            
        finally:
            self._release_lock(lock)
    
    @transaction.atomic
    def reverse_transaction(self, ledger_entry_id, reason, created_by):
        """
        Reverse a transaction by creating a new reversal entry.
        Never modifies the original entry.
        """
        original_entry = LedgerEntry.objects.get(id=ledger_entry_id)
        
        # Create reversal entry
        reversal_entry = LedgerEntry.objects.create(
            group=original_entry.group,
            member=original_entry.member,
            entry_type=original_entry.entry_type,
            amount=-original_entry.amount,  # Reverse the amount
            description=f"REVERSAL: {original_entry.description} - {reason}",
            reference=original_entry.reference,
            created_by=created_by,
            is_reversal=True,
            reversed_by=original_entry,
        )
        
        # Create reverse double-entry
        if original_entry.debit_entry:
            # Reverse: credit what was debited, debit what was credited
            CreditEntry.objects.create(
                ledger_entry=reversal_entry,
                account=original_entry.debit_entry.account,
                amount=abs(original_entry.amount)
            )
        
        if original_entry.credit_entry:
            DebitEntry.objects.create(
                ledger_entry=reversal_entry,
                account=original_entry.credit_entry.account,
                amount=abs(original_entry.amount)
            )
        
        return reversal_entry
    
    def get_group_balance(self, group_id):
        """Get group balance (cached)."""
        cache_key = f'group:{group_id}:balance'
        balance = cache.get(cache_key)
        
        if balance is None:
            group = Group.objects.get(id=group_id)
            balance = group.balance_cache
            cache.set(cache_key, balance, 300)  # 5 minutes
        
        return balance
    
    def reconcile_balance(self, group_id):
        """
        Reconcile balance_cache with sum of ledger entries.
        Returns (calculated_balance, cached_balance, difference)
        """
        group = Group.objects.get(id=group_id)
        
        # Calculate from ledger entries
        calculated_balance = LedgerEntry.objects.filter(
            group=group
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        cached_balance = group.balance_cache
        difference = calculated_balance - cached_balance
        
        return calculated_balance, cached_balance, difference
