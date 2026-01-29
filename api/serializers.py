"""
API Serializers for TaawaVault.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from core.models import (
    Group, Membership, LedgerEntry, DebitEntry, CreditEntry,
    Profile, ConsentRecord
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for Profile model."""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Profile
        fields = ['id', 'user', 'full_name', 'phone_country_code', 'phone_number', 'has_seen_instructions']
        read_only_fields = ['id']


class GroupSerializer(serializers.ModelSerializer):
    """Serializer for Group model."""
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'currency', 'balance_cache',
            'data_residency', 'consent_required', 'created_at', 'updated_at',
            'members_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'balance_cache']
    
    def get_members_count(self, obj):
        return Membership.objects.filter(group=obj, deleted_at__isnull=True).count()


class MembershipSerializer(serializers.ModelSerializer):
    """Serializer for Membership model."""
    user = UserSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    group_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Membership
        fields = [
            'id', 'user', 'group', 'group_id', 'role', 'title',
            'joined_at', 'deleted_at'
        ]
        read_only_fields = ['id', 'joined_at', 'deleted_at']


class DebitEntrySerializer(serializers.ModelSerializer):
    """Serializer for DebitEntry model."""
    class Meta:
        model = DebitEntry
        fields = ['id', 'account', 'amount', 'created_at']
        read_only_fields = ['id', 'created_at']


class CreditEntrySerializer(serializers.ModelSerializer):
    """Serializer for CreditEntry model."""
    class Meta:
        model = CreditEntry
        fields = ['id', 'account', 'amount', 'created_at']
        read_only_fields = ['id', 'created_at']


class LedgerEntrySerializer(serializers.ModelSerializer):
    """Serializer for LedgerEntry model."""
    member = MembershipSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    debit_entry = DebitEntrySerializer(read_only=True)
    credit_entry = CreditEntrySerializer(read_only=True)
    
    class Meta:
        model = LedgerEntry
        fields = [
            'id', 'group', 'member', 'entry_type', 'amount', 'description',
            'reference', 'contribution_category', 'source', 'attachment',
            'occurred_at', 'created_at', 'created_by', 'transaction_id',
            'is_reversal', 'reversed_by', 'debit_entry', 'credit_entry'
        ]
        read_only_fields = [
            'id', 'created_at', 'transaction_id', 'is_reversal',
            'debit_entry', 'credit_entry'
        ]


class ContributionSerializer(serializers.Serializer):
    """Serializer for contribution creation."""
    group_id = serializers.IntegerField()
    member_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(max_length=255)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    transaction_id = serializers.UUIDField(required=False)


class ExpenseSerializer(serializers.Serializer):
    """Serializer for expense creation."""
    group_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(max_length=255)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    transaction_id = serializers.UUIDField(required=False)


class ConsentRecordSerializer(serializers.ModelSerializer):
    """Serializer for ConsentRecord model."""
    class Meta:
        model = ConsentRecord
        fields = [
            'id', 'user', 'purpose', 'granted', 'granted_at',
            'revoked_at', 'consent_text', 'version', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
