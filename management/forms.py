from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date
from .models import (
    Trip, 
    TripExpense, 
    Vehicle, 
    Driver, 
    PartyMaster,
    AccountMaster,
    ExpenseCategory, 
    AccountTransaction,
    MaintenanceExpense
)

# ----------------------------------------------------------------------
# 1. Trip Creation Form
# ----------------------------------------------------------------------
class TripForm(forms.ModelForm):
    # Explicitly define date field to use the HTML5 date picker
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    
    client = forms.ModelChoiceField(
        queryset=PartyMaster.objects.filter(party_type='CLIENT'),
        required=True,
        empty_label="Select Client (Consignor)",
        label="Client (Consignor)",
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.all(), 
        required=True, 
        empty_label="Select Vehicle",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    driver = forms.ModelChoiceField(
        queryset=Driver.objects.all(), 
        required=True, 
        empty_label="Select Driver",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    transporter = forms.ModelChoiceField(
        queryset=PartyMaster.objects.filter(party_type='TRANSPORTER'), 
        required=True, 
        empty_label="Select Transporter",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Trip
        fields = [
            'date', 'client', 'vehicle', 'driver', 'transporter', 'origin', 
            'destination', 'rate', 'weight', 'advance', 'status'
        ]
        
        widgets = {
            'origin': forms.TextInput(attrs={'class': 'form-control'}),
            'destination': forms.TextInput(attrs={'class': 'form-control'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'advance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

# ----------------------------------------------------------------------
# 2. Trip Expense Form
# ----------------------------------------------------------------------
class TripExpenseForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    
    class Meta:
        model = TripExpense
        fields = [
            'date', 
            'expense_category', 
            'amount', 
            'paid_via_account', 
            'description'
        ]
        
        widgets = {
            'expense_category': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'paid_via_account': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make Paid Via Account NOT required (allows for cash/driver pocket expenses)
        self.fields['paid_via_account'].required = False

# ----------------------------------------------------------------------
# 3. Expense Category Form
# ----------------------------------------------------------------------
class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'is_trip_expense']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_trip_expense': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# ----------------------------------------------------------------------
# 4. Maintenance Expense Form
# ----------------------------------------------------------------------
class MaintenanceExpenseForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    
    workshop = forms.ModelChoiceField(
        queryset=PartyMaster.objects.filter(party_type__in=['WORKSHOP', 'OTHER']),
        label="Workshop/Vendor",
        empty_label="Select Workshop/Vendor",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True 
    )

    class Meta:
        model = MaintenanceExpense
        fields = [
            'date', 'vehicle', 'workshop', 'expense_category', 'description', 
            'shop', 'amount', 'is_paid', 'payment_date', 'paid_via_account'
        ]
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-control'}),
            'expense_category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'shop': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'paid_via_account': forms.Select(attrs={'class': 'form-control'}),
        }

# ----------------------------------------------------------------------
# 5. Account Master Form
# ----------------------------------------------------------------------
class AccountMasterForm(forms.ModelForm):
    class Meta:
        model = AccountMaster
        fields = ['account_name', 'account_type', 'initial_balance', 'is_active']
        widgets = {
            'account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'initial_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# ----------------------------------------------------------------------
# 6. Account Transfer Form
# ----------------------------------------------------------------------
class AccountTransferForm(forms.ModelForm):
    from_account = forms.ModelChoiceField(
        queryset=AccountMaster.objects.all(),
        label="From Account (Source)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    to_account = forms.ModelChoiceField(
        queryset=AccountMaster.objects.all(),
        label="To Account (Destination)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = AccountTransaction
        fields = ['date', 'withdrawal', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'withdrawal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), 
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Bank to Fastag Top-up'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['withdrawal'].label = "Transfer Amount (₹)"

    def clean(self):
        cleaned_data = super().clean()
        from_account = cleaned_data.get('from_account')
        to_account = cleaned_data.get('to_account')

        if from_account and to_account and from_account == to_account:
            raise ValidationError("The Source and Destination accounts must be different for a transfer.")
        
        return cleaned_data
    
# ----------------------------------------------------------------------
# 7. Advance Receipt Form (Non-Model Form)
# ----------------------------------------------------------------------
class AdvanceReceiptForm(forms.Form):
    # This field is now the actual amount being received
    amount = forms.DecimalField(
        label="Amount Receiving Now (₹)", # Changed Label
        max_digits=10,
        decimal_places=2,
        required=True,
        # REMOVED: readonly='readonly' attribute
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}) 
    )
    date = forms.DateField(
        label="Date of Receipt",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    account = forms.ModelChoiceField(
        queryset=AccountMaster.objects.all(),
        label="Deposit Into Account",
        required=True,
        empty_label="Select Account",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
# ----------------------------------------------------------------------
# 8. Party Master Form
# ----------------------------------------------------------------------
class PartyMasterForm(forms.ModelForm):
    class Meta:
        model = PartyMaster
        fields = [
            'name', 'party_type', 'contact_person', 'phone_number', 
            'email', 'address', 'gst_number'
        ]
        widgets = {
            'party_type': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['party_type']:
                field.widget.attrs['class'] = 'form-control'

# ----------------------------------------------------------------------
# 9. Vehicle Form
# ----------------------------------------------------------------------
class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            'vehicle_no', 'vehicle_type', 'ownership', 'owner_name', 'hypothecation',
            'reg_date', 'fitness_expiry', 'permit_expiry', 'insurance_expiry',
            'national_permit', 'puc_expiry', 'tax_expiry'
        ]
        widgets = {
            'vehicle_no': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_type': forms.TextInput(attrs={'class': 'form-control'}),
            'ownership': forms.TextInput(attrs={'class': 'form-control'}),
            'owner_name': forms.TextInput(attrs={'class': 'form-control'}),
            'hypothecation': forms.TextInput(attrs={'class': 'form-control'}),
            'national_permit': forms.TextInput(attrs={'class': 'form-control'}),
            # Date Fields
            'reg_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fitness_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'permit_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'insurance_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'puc_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tax_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

# ----------------------------------------------------------------------
# 10. Driver Master Form
# ----------------------------------------------------------------------
class DriverForm(forms.ModelForm):
    license_expiry = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    class Meta:
        model = Driver
        fields = [
            'driver_id', 'name', 'mobile', 'license_no', 
            'license_expiry', 'fixed_salary', 'wage_rate', 'is_active'
        ]
        widgets = {
            'driver_id': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'license_no': forms.TextInput(attrs={'class': 'form-control'}),
            'fixed_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'wage_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# ----------------------------------------------------------------------
# 11. Trip Settlement Form (NEW)
# ----------------------------------------------------------------------
class TripSettlementForm(forms.Form):
    """
    Form to handle the final closure of a trip and collection of balance payment.
    """
    # Read-only fields for display
    total_freight = forms.DecimalField(label="Total Freight", disabled=True, required=False)
    advance_received = forms.DecimalField(label="Total Advance Received", disabled=True, required=False)
    balance_due = forms.DecimalField(label="Calculated Balance Due", disabled=True, required=False)

    # Input fields
    shortage_damage = forms.DecimalField(
        label="Deductions (Shortage/Damage)", 
        initial=0.00, 
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    received_amount = forms.DecimalField(
        label="Amount Receiving Now", 
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    payment_date = forms.DateField(
        label="Date of Receipt",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=date.today
    )
    
    account = forms.ModelChoiceField(
        queryset=AccountMaster.objects.filter(is_active=True),
        label="Deposit into Account",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Any settlement notes...'})
    )