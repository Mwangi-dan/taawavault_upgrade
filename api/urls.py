"""
API URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GroupViewSet, MembershipViewSet, LedgerEntryViewSet,
    TokenObtainPairView, TokenRefreshView
)

router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'memberships', MembershipViewSet, basename='membership')
router.register(r'ledger', LedgerEntryViewSet, basename='ledgerentry')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
