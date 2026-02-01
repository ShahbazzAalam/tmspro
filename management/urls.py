# C:\Users\Alam\tms_project\management\urls.py

from django.urls import path
from . import views

urlpatterns = [
    # 1. Dashboard / Trip List (Homepage for the app)
    path('', views.trip_list, name='trip_list'),
    
    # --- Trip URLs ---
    path('trip/new/', views.trip_create, name='trip_create'),
    path('trip/<str:trip_id>/', views.trip_detail, name='trip_detail'),
    path('trip/<str:trip_id>/edit/', views.trip_update, name='trip_update'),
    path('trip/<str:trip_id>/record-advance/', views.trip_record_advance, name='trip_record_advance'),
    path('trip/<str:trip_id>/complete/', views.trip_status_complete, name='trip_status_complete'),
    path('trip/<str:trip_id>/revert/', views.trip_status_revert, name='trip_status_revert'),
    path('trip/<str:trip_id>/expense/new/', views.trip_expense_create, name='trip_expense_create'),
    
    # --- Account Master URLs ---
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/create/', views.account_create, name='account_create'),
    path('accounts/transfer/', views.account_transfer, name='account_transfer'),
    path('accounts/<int:account_id>/', views.account_detail, name='account_detail'),
    path('accounts/<int:account_id>/edit/', views.account_update, name='account_update'),

    # --- Party Master URLs (Clients/Transporters/Workshops) ---
    path('parties/', views.party_list, name='party_list'),
    path('parties/create/', views.party_create, name='party_create'),
    path('parties/<int:pk>/', views.party_detail, name='party_detail'),
    path('parties/<int:pk>/edit/', views.party_update, name='party_update'),
    path('parties/<int:pk>/delete/', views.party_delete, name='party_delete'),

    # --- Expense Category URLs ---
    path('category/list/', views.expense_category_list, name='expense_category_list'),
    path('category/new/', views.expense_category_create, name='expense_category_create'),
    path('category/<int:pk>/update/', views.expense_category_update, name='expense_category_update'),

    # --- Vehicle Management URLs (Vehicle Master) ---
    path('vehicles/', views.vehicle_list, name='vehicle_list'), # Used as the main list page
    path('vehicle/new/', views.vehicle_create, name='vehicle_create'),
    # Note: <str:pk> is correct for vehicle_no (alphanumeric primary key)
    path('vehicle/<str:pk>/update/', views.vehicle_update, name='vehicle_update'),

    # --- Maintenance Expense Paths ---
    path('maintenance/list/', views.maintenance_expense_list, name='maintenance_expense_list'),
    path('maintenance/new/', views.maintenance_expense_create, name='maintenance_expense_create'),

    # --- Driver Master URLs ---
    path('drivers/', views.driver_list, name='driver_list'),
    path('drivers/new/', views.driver_create, name='driver_create'),
    # Note the use of <str:pk> because driver_id is the primary key (alphanumeric)
    path('drivers/<str:pk>/update/', views.driver_update, name='driver_update'),

    path('drivers/<str:pk>/delete/', views.driver_delete, name='driver_delete'),

    

    path('trip/<str:pk>/settlement/', views.trip_final_settlement, name='trip_final_settlement'),





]