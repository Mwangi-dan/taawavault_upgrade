"""
API Views for TaawaVault.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from core.models import Group, Membership, LedgerEntry
from core.services import FinancialService, ReportService
from .serializers import (
    GroupSerializer, MembershipSerializer, LedgerEntrySerializer,
    ContributionSerializer, ExpenseSerializer
)


class TokenObtainPairView(BaseTokenObtainPairView):
    """Custom token obtain view with additional user info."""
    pass


class TokenRefreshView(BaseTokenRefreshView):
    """Token refresh view."""
    pass


class GroupViewSet(viewsets.ModelViewSet):
    """ViewSet for Group model."""
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return groups user is a member of."""
        if self.request.user.is_superuser:
            return Group.objects.all()
        return Group.objects.filter(
            memberships__user=self.request.user,
            memberships__deleted_at__isnull=True
        ).distinct()
    
    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Get group balance."""
        group = self.get_object()
        financial_service = FinancialService()
        balance = financial_service.get_group_balance(group.id)
        return Response({'balance': str(balance)})
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get group summary statistics."""
        group = self.get_object()
        
        total_contributions = LedgerEntry.objects.filter(
            group=group,
            entry_type='CONTRIBUTION'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_expenses = LedgerEntry.objects.filter(
            group=group,
            entry_type='EXPENSE'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        members_count = Membership.objects.filter(
            group=group,
            deleted_at__isnull=True
        ).count()
        
        return Response({
            'balance': str(group.balance_cache),
            'total_contributions': str(total_contributions),
            'total_expenses': str(total_expenses),
            'members_count': members_count,
        })


class MembershipViewSet(viewsets.ModelViewSet):
    """ViewSet for Membership model."""
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return memberships based on user access."""
        group_id = self.request.query_params.get('group_id')
        
        if self.request.user.is_superuser:
            queryset = Membership.objects.all()
        else:
            queryset = Membership.objects.filter(
                group__memberships__user=self.request.user,
                group__memberships__deleted_at__isnull=True
            ).distinct()
        
        if group_id:
            queryset = queryset.filter(group_id=group_id, deleted_at__isnull=True)
        
        return queryset.select_related('user', 'group')


class LedgerEntryViewSet(viewsets.ModelViewSet):
    """ViewSet for LedgerEntry model."""
    serializer_class = LedgerEntrySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return ledger entries based on user access."""
        group_id = self.request.query_params.get('group_id')
        
        if self.request.user.is_superuser:
            queryset = LedgerEntry.objects.all()
        else:
            queryset = LedgerEntry.objects.filter(
                group__memberships__user=self.request.user,
                group__memberships__deleted_at__isnull=True
            ).distinct()
        
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        
        return queryset.select_related('group', 'member__user', 'created_by')
    
    @action(detail=False, methods=['post'])
    def contribution(self, request):
        """Create a contribution transaction."""
        serializer = ContributionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        financial_service = FinancialService()
        ledger_entry = financial_service.create_contribution(
            group_id=serializer.validated_data['group_id'],
            member_id=serializer.validated_data['member_id'],
            amount=serializer.validated_data['amount'],
            description=serializer.validated_data['description'],
            created_by=request.user,
            reference=serializer.validated_data.get('reference'),
        )
        
        return Response(
            LedgerEntrySerializer(ledger_entry).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def expense(self, request):
        """Create an expense transaction."""
        serializer = ExpenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        financial_service = FinancialService()
        try:
            ledger_entry = financial_service.create_expense(
                group_id=serializer.validated_data['group_id'],
                amount=serializer.validated_data['amount'],
                description=serializer.validated_data['description'],
                created_by=request.user,
                reference=serializer.validated_data.get('reference'),
            )
            
            return Response(
                LedgerEntrySerializer(ledger_entry).data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """Reverse a transaction."""
        ledger_entry = self.get_object()
        reason = request.data.get('reason', 'Reversal requested')
        
        financial_service = FinancialService()
        reversal_entry = financial_service.reverse_transaction(
            ledger_entry_id=ledger_entry.id,
            reason=reason,
            created_by=request.user,
        )
        
        return Response(
            LedgerEntrySerializer(reversal_entry).data,
            status=status.HTTP_201_CREATED
        )
