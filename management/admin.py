from django.contrib import admin
from .models import (
    Vehicle, Driver, Trip, TripExpense, PartyMaster, 
    ExpenseCategory, AccountMaster, MaintenanceExpense, 
    DocketTable, AccountTransaction
)

# --- INLINE ADMINS ---

# Inline for adding multiple expenses directly on the Trip creation page (Optional but useful)
# class TripExpenseInline(admin.TabularInline):
#     model = TripExpense
#     extra = 1 # Number of empty forms to display

# --- BASE ADMIN MODELS ---

# 1. Vehicle Admin
@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        'vehicle_no', 'vehicle_type', 'ownership', 'fitness_expiry', 'puc_expiry', 
        'tax_expiry'
    )
    search_fields = ('vehicle_no', 'owner_name')
    list_filter = ('ownership',)
    date_hierarchy = 'reg_date'


# 2. Driver Admin
@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('driver_id', 'name', 'mobile', 'license_expiry', 'is_active')
    search_fields = ('driver_id', 'name', 'mobile')
    list_filter = ('is_active',)


# --- NEW MASTER DATA ADMINS ---

# 3. PartyMaster (Transporters, Workshops, Vendors)
@admin.register(PartyMaster)
class PartyMasterAdmin(admin.ModelAdmin):
    list_display = ('name', 'party_type', 'nick_name', 'commission_rate', 'orai_charge')
    list_filter = ('party_type',)
    search_fields = ('name', 'nick_name', 'pan_number')
    
    # Fieldsets to group related fields for a cleaner interface
    fieldsets = (
        ('Party Identification', {
            'fields': ('party_type', 'name', 'nick_name', 'contact_person', 'address'),
        }),
        ('Financial/Tax Details', {
            'fields': ('pan_number', 'bank_account_no', 'ifsc_code'),
        }),
        ('Transporter Rates (if applicable)', {
            'fields': ('commission_rate', 'orai_charge'),
            'description': 'Only enter values if Party Type is "Transporter".'
        }),
    )


# 4. ExpenseCategory Admin
@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_trip_expense')
    list_filter = ('is_trip_expense',)


# 5. AccountMaster Admin
@admin.register(AccountMaster)
class AccountMasterAdmin(admin.ModelAdmin):
    list_display = ('account_name', 'account_type', 'initial_balance', 'is_active')
    list_filter = ('account_type', 'is_active')
    search_fields = ('account_name',)


# --- TRANSACTION & OPERATIONAL ADMINS ---

# 6. Trip Admin (Modified)
@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        'trip_id', 'date', 'vehicle', 'driver', 'transporter', 'origin', 
        'destination', 'total_freight', 'advance', 'status'
    )
    # The calculated fields are readonly
    readonly_fields = ('trip_id', 'total_freight', 'commission_amount', 'orai_amount')
    list_filter = ('status', 'vehicle', 'transporter')
    search_fields = ('trip_id', 'vehicle__vehicle_no', 'driver__name', 'origin', 'destination')
    # inlines = [TripExpenseInline] # Uncomment this line if you want the inline form

# 7. Trip Expense Admin (FIXED the ERROR by removing total_trip_expense)
@admin.register(TripExpense)
class TripExpenseAdmin(admin.ModelAdmin):
    list_display = ('trip', 'date', 'expense_category', 'amount', 'paid_via_account')
    search_fields = ('trip__trip_id', 'description')
    list_filter = ('expense_category', 'paid_via_account')


# 8. MaintenanceExpense Admin
@admin.register(MaintenanceExpense)
class MaintenanceExpenseAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'vehicle', 'workshop', 'amount', 'is_paid', 'payment_date', 'paid_via_account'
    )
    list_filter = ('is_paid', 'workshop', 'expense_category')
    search_fields = ('vehicle__vehicle_no', 'workshop__name', 'description')
    readonly_fields = ('payment_date', 'paid_via_account') # These are auto-filled on payment via AccountTransaction


# 9. DocketTable Admin
@admin.register(DocketTable)
class DocketTableAdmin(admin.ModelAdmin):
    list_display = (
        'docket_no', 'trip', 'send_date', 'challan_received', 'received_date'
    )
    list_filter = ('challan_received',)
    search_fields = ('docket_no', 'trip__trip_id')
    date_hierarchy = 'send_date'


# 10. AccountTransaction Admin
@admin.register(AccountTransaction)
class AccountTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'description', 'from_account', 'to_account', 'deposit', 'withdrawal'
    )
    search_fields = ('description', 'from_account__account_name', 'to_account__account_name')
    list_filter = ('from_account', 'to_account')
    date_hierarchy = 'date'