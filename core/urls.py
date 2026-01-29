"""
URL configuration for core app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('', views.dashboard, name='dashboard'),
    path('groups/', views.group_list, name='group_list'),
    path('groups/<int:group_id>/', views.group_detail, name='group_detail'),
    path('groups/<int:group_id>/ledger/', views.ledger_list, name='ledger_list'),
    path('groups/<int:group_id>/members/', views.member_list, name='member_list'),
    path('groups/<int:group_id>/reports/', views.reports, name='reports'),
]
