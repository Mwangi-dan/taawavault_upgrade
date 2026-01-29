"""
Core models for TaawaVault.
Implements double-entry accounting, multi-tenant isolation, and compliance features.
"""
import uuid
import hashlib
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from fernet_fields import EncryptedCharField
from auditlog.registry import auditlog


class Group(models.Model):
    """Represents a financial group/cooperative."""
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('KES', 'Kenyan Shilling'),
        ('UGX', 'Ugandan Shilling'),
        ('TZS', 'Tanzanian Shilling'),
    ]
    
    DATA_RESIDENCY_CHOICES = [
        ('KENYA', 'Kenya'),
        ('EU', 'European Union'),
        ('US', 'United States'),
        ('GLOBAL', 'Global'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='KES')
    balance_cache = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    version = models.PositiveIntegerField(default=1)  # Optimistic locking
    data_residency = models.CharField(max_length=10, choices=DATA_RESIDENCY_CHOICES, default='KENYA')
    consent_required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_group'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(balance_cache__gte=0),
                name='positive_balance'
            ),
        ]
    
    def __str__(self):
        return self.name


class Profile(models.Model):
    """Extended user information with encrypted PII."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = EncryptedCharField(max_length=150, blank=True)
    phone_country_code = EncryptedCharField(max_length=5, blank=True)
    phone_number = EncryptedCharField(max_length=30, blank=True)
    has_seen_instructions = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_profile'
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class Membership(models.Model):
    """Links Users to Groups with roles."""
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('TREASURER', 'Treasurer'),
        ('MEMBER', 'Member'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default='MEMBER')
    title = models.CharField(max_length=50, blank=True, null=True)
    version = models.PositiveIntegerField(default=1)  # Optimistic locking
    deleted_at = models.DateTimeField(null=True, blank=True)  # Soft delete
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_membership'
        indexes = [
            models.Index(
                fields=['user', 'group'],
                condition=models.Q(deleted_at__isnull=True),
                name='core_memb_user_grp_active',
            ),
            models.Index(
                fields=['group', 'role'],
                condition=models.Q(deleted_at__isnull=True),
                name='core_memb_grp_role_active',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'group'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_active_membership'
            ),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.group.name} ({self.role})"


class LedgerEntry(models.Model):
    """Core financial transaction record (IMMUTABLE, APPEND-ONLY)."""
    ENTRY_TYPE_CHOICES = [
        ('CONTRIBUTION', 'Contribution'),
        ('EXPENSE', 'Expense'),
        ('PENALTY', 'Penalty'),
        ('DIVIDEND', 'Dividend'),
        ('LOAN', 'Loan'),
        ('LOAN_REPAYMENT', 'Loan Repayment'),
        ('INTEREST', 'Interest'),
        ('OTHER', 'Other'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='ledger_entries')
    member = models.ForeignKey(Membership, on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    description = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, blank=True, null=True)
    contribution_category = models.CharField(max_length=50, blank=True, null=True)
    source = models.CharField(max_length=100, blank=True, null=True)
    attachment = models.FileField(upload_to='ledger_entries/%Y/%m/', blank=True, null=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_ledger_entries')
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)  # Idempotency
    hash_prev_tx = models.CharField(max_length=64, blank=True, null=True)  # Cryptographic chain
    is_reversal = models.BooleanField(default=False)
    reversed_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reversals')
    
    class Meta:
        db_table = 'core_ledgerentry'
        indexes = [
            models.Index(fields=['group', 'occurred_at', 'amount'], name='idx_ledger_group_date_amount'),
            models.Index(fields=['member', 'group', 'occurred_at'], name='idx_ledger_member_group'),
            models.Index(fields=['transaction_id'], name='idx_ledger_transaction_id'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='positive_amount'
            ),
        ]
        ordering = ['-occurred_at', '-created_at']
    
    def __str__(self):
        return f"{self.entry_type} - {self.amount} ({self.group.name})"


class DebitEntry(models.Model):
    """Debit side of double-entry accounting."""
    ACCOUNT_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank'),
        ('MEMBER_LOANS_RECEIVABLE', 'Member Loans Receivable'),
        ('EXPENSES', 'Expenses'),
        ('ADMINISTRATIVE', 'Administrative'),
        ('MEETING', 'Meeting'),
        ('EMERGENCY', 'Emergency'),
        ('PENALTIES', 'Penalties'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    ledger_entry = models.OneToOneField(LedgerEntry, on_delete=models.CASCADE, related_name='debit_entry')
    account = models.CharField(max_length=50, choices=ACCOUNT_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_debitentry'
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='positive_debit_amount'
            ),
        ]
    
    def __str__(self):
        return f"Debit: {self.account} - {self.amount}"


class CreditEntry(models.Model):
    """Credit side of double-entry accounting."""
    ACCOUNT_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank'),
        ('MEMBER_CONTRIBUTIONS', 'Member Contributions'),
        ('MEMBER_LOANS_PAYABLE', 'Member Loans Payable'),
        ('GROUP_EQUITY', 'Group Equity'),
        ('INVESTMENT_INTEREST', 'Investment Interest'),
        ('INVESTMENT_DIVIDEND', 'Investment Dividend'),
        ('BANK_INTEREST', 'Bank Interest'),
        ('OTHER_INCOME', 'Other Income'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    ledger_entry = models.OneToOneField(LedgerEntry, on_delete=models.CASCADE, related_name='credit_entry')
    account = models.CharField(max_length=50, choices=ACCOUNT_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_creditentry'
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='positive_credit_amount'
            ),
        ]
    
    def __str__(self):
        return f"Credit: {self.account} - {self.amount}"


class BalanceCache(models.Model):
    """Cached group balance with constraints."""
    id = models.BigAutoField(primary_key=True)
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='balance_cache_obj')
    balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    last_updated = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)  # Optimistic locking
    
    class Meta:
        db_table = 'core_balancecache'
        constraints = [
            models.CheckConstraint(
                check=models.Q(balance__gte=0),
                name='positive_balance_cache'
            ),
        ]
    
    def __str__(self):
        return f"Balance: {self.balance} ({self.group.name})"


class TransactionHash(models.Model):
    """Cryptographic hash chain for transaction verification."""
    id = models.BigAutoField(primary_key=True)
    ledger_entry = models.OneToOneField(LedgerEntry, on_delete=models.CASCADE, related_name='transaction_hash')
    hash_value = models.CharField(max_length=64)  # SHA-256
    hash_prev_tx = models.CharField(max_length=64, blank=True, null=True)  # Chain link
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_transactionhash'
        indexes = [
            models.Index(fields=['hash_prev_tx'], name='idx_transaction_hash_prev'),
        ]
    
    def __str__(self):
        return f"Hash: {self.hash_value[:16]}..."


class ConsentRecord(models.Model):
    """Track user consent for data processing (DPA compliance)."""
    PURPOSE_CHOICES = [
        ('WHATSAPP_NOTIFICATION', 'WhatsApp Notification'),
        ('EMAIL_MARKETING', 'Email Marketing'),
        ('THIRD_PARTY_SHARING', 'Third Party Sharing'),
        ('ANALYTICS', 'Analytics'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consent_records')
    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES)
    granted = models.BooleanField(default=False)
    granted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    consent_text = models.TextField()
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_consentrecord'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'purpose'],
                condition=models.Q(revoked_at__isnull=True),
                name='unique_active_consent'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'purpose']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.purpose} ({'Granted' if self.granted else 'Revoked'})"


class AuditLog(models.Model):
    """Comprehensive audit trail (IMMUTABLE)."""
    EVENT_TYPE_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField()
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    before_value = models.JSONField(null=True, blank=True)
    after_value = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    event_hash = models.CharField(max_length=64, blank=True)  # Tamper detection
    
    class Meta:
        db_table = 'core_auditlog'
        indexes = [
            models.Index(fields=['group', 'timestamp'], name='idx_auditlog_group_timestamp'),
            models.Index(fields=['user', 'timestamp'], name='idx_auditlog_user_timestamp'),
            models.Index(fields=['event_type', 'timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.event_type} - {self.model_name} ({self.timestamp})"


class EventStore(models.Model):
    """Immutable event store for event sourcing."""
    EVENT_TYPE_CHOICES = [
        ('FINANCIAL_EVENT', 'Financial Event'),
        ('MEMBERSHIP_EVENT', 'Membership Event'),
        ('PERMISSION_EVENT', 'Permission Event'),
        ('SYSTEM_EVENT', 'System Event'),
        ('COMPLIANCE_EVENT', 'Compliance Event'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    aggregate_id = models.PositiveIntegerField()  # Group ID or Membership ID
    aggregate_type = models.CharField(max_length=50)  # Group, Membership, etc.
    event_data = models.JSONField()
    event_version = models.PositiveIntegerField()
    occurred_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_events')
    event_hash = models.CharField(max_length=64)  # Cryptographic chain
    hash_prev_event = models.CharField(max_length=64, null=True, blank=True)  # Previous event hash
    
    class Meta:
        db_table = 'core_eventstore'
        indexes = [
            models.Index(fields=['aggregate_id', 'event_version'], name='idx_evstore_agg_version'),
            models.Index(fields=['event_type', 'occurred_at']),
        ]
        ordering = ['aggregate_id', 'event_version']
    
    def __str__(self):
        return f"{self.event_type} - {self.aggregate_type}:{self.aggregate_id} (v{self.event_version})"


# Register models with auditlog
auditlog.register(Group)
auditlog.register(Membership)
auditlog.register(LedgerEntry)
auditlog.register(ConsentRecord)
