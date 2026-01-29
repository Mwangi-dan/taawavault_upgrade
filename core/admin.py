"""
Django admin configuration for core models.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    Group, Profile, Membership, LedgerEntry, DebitEntry, CreditEntry,
    BalanceCache, TransactionHash, ConsentRecord, AuditLog, EventStore
)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'currency', 'balance_cache', 'data_residency', 'created_at']
    list_filter = ['currency', 'data_residency', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'balance_cache', 'version']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'phone_number', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'role', 'joined_at', 'deleted_at']
    list_filter = ['role', 'deleted_at', 'joined_at']
    search_fields = ['user__username', 'group__name']
    readonly_fields = ['joined_at', 'version']


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'entry_type', 'amount', 'description', 'occurred_at', 'created_at']
    list_filter = ['entry_type', 'occurred_at', 'created_at']
    search_fields = ['description', 'reference']
    readonly_fields = ['created_at', 'transaction_id', 'hash_prev_tx', 'is_reversal']
    date_hierarchy = 'occurred_at'


@admin.register(DebitEntry)
class DebitEntryAdmin(admin.ModelAdmin):
    list_display = ['ledger_entry', 'account', 'amount', 'created_at']
    list_filter = ['account', 'created_at']
    readonly_fields = ['created_at']


@admin.register(CreditEntry)
class CreditEntryAdmin(admin.ModelAdmin):
    list_display = ['ledger_entry', 'account', 'amount', 'created_at']
    list_filter = ['account', 'created_at']
    readonly_fields = ['created_at']


@admin.register(BalanceCache)
class BalanceCacheAdmin(admin.ModelAdmin):
    list_display = ['group', 'balance', 'last_updated', 'version']
    readonly_fields = ['last_updated', 'version']


@admin.register(TransactionHash)
class TransactionHashAdmin(admin.ModelAdmin):
    list_display = ['ledger_entry', 'hash_value', 'created_at']
    readonly_fields = ['created_at', 'hash_value']


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'purpose', 'granted', 'granted_at', 'revoked_at']
    list_filter = ['purpose', 'granted', 'granted_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'version']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'model_name', 'user', 'group', 'timestamp']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['model_name', 'user__username']
    readonly_fields = ['timestamp', 'event_hash']
    date_hierarchy = 'timestamp'


@admin.register(EventStore)
class EventStoreAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'aggregate_type', 'aggregate_id', 'event_version', 'occurred_at']
    list_filter = ['event_type', 'aggregate_type', 'occurred_at']
    readonly_fields = ['occurred_at', 'event_hash', 'hash_prev_event']
    date_hierarchy = 'occurred_at'
