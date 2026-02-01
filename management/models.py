from django.db import models
from django.db.models import Max
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

# --- CONSTANTS ---
PARTY_TYPE_CHOICES = [
    ('TRANSPORTER', 'Transporter (Hired Carrier)'),
    ('WORKSHOP', 'Workshop / Service Vendor'),
    ('CLIENT', 'Client / Consignor'),
    ('OTHER', 'Other Vendor'),
]

ACCOUNT_TYPE_CHOICES = [
    ('BANK', 'Bank Account'),
    ('CASH', 'Cash / Petty Cash'),
    ('FASTAG', 'Fastag Wallet'),
    ('DIESELCARD', 'Diesel Card Wallet'),
]

TRIP_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('IN_TRANSIT', 'In-transit'),
    ('COMPLETED', 'Completed'),
    ('CANCELLED', 'Cancelled'),
]


# =========================================================================
# A. MASTER DATA TABLES
# =========================================================================

# --- 1. Vehicle Master ---
class Vehicle(models.Model):
    vehicle_no = models.CharField(
        max_length=15, unique=True, primary_key=True, verbose_name="Vehicle Number"
    )
    vehicle_type = models.CharField(max_length=50)
    ownership = models.CharField(max_length=20, default='Own')
    owner_name = models.CharField(max_length=100, blank=True, null=True)
    hypothecation = models.CharField(max_length=100, blank=True, null=True, verbose_name="Hypothecation Details")
    
    # Expiry Dates
    reg_date = models.DateField(blank=True, null=True, verbose_name="Registration Date")
    fitness_expiry = models.DateField(blank=True, null=True, verbose_name="Fitness Expiry")
    permit_expiry = models.DateField(blank=True, null=True, verbose_name="Permit Expiry")
    insurance_expiry = models.DateField(blank=True, null=True, verbose_name="Insurance Expiry")
    national_permit = models.CharField(max_length=50, blank=True, null=True)
    puc_expiry = models.DateField(blank=True, null=True, verbose_name="PUC Expiry")
    tax_expiry = models.DateField(blank=True, null=True, verbose_name="Tax Expiry")

    def __str__(self):
        return self.vehicle_no


# --- 2. Driver Master ---
class Driver(models.Model):
    driver_id = models.CharField(
        max_length=10,
        unique=True,
        primary_key=True,
        verbose_name="Driver ID"
    )
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15)
    license_no = models.CharField(max_length=50, unique=True)
    license_expiry = models.DateField()
    fixed_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    wage_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.driver_id})"


# --- 3. Party Master ---
class PartyMaster(models.Model):
    party_type = models.CharField(
        max_length=20, choices=PARTY_TYPE_CHOICES, default='OTHER', verbose_name="Party Type (Role)"
    )
    name = models.CharField(max_length=100, verbose_name="Company/Vendor Name")
    nick_name = models.CharField(max_length=50, blank=True, null=True)
    
    # Contact/Address
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gst_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="GST Number")
    
    # Financial/Tax Details
    pan_number = models.CharField(max_length=10, blank=True, null=True, verbose_name="PAN/Tax ID")
    bank_account_no = models.CharField(max_length=30, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="IFSC Code")

    # Transporter-specific fields
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'), verbose_name="Commission %"
    )
    orai_charge = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Orai Fixed Charge"
    )

    def __str__(self):
        return f"{self.name} ({self.party_type})"


# --- 4. Expense Category ---
class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_trip_expense = models.BooleanField(
        default=True, verbose_name="Related to Trip Cost (P&L)"
    )

    def __str__(self):
        return self.name


# --- 5. Account Master ---
class AccountMaster(models.Model):
    account_name = models.CharField(max_length=100, unique=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='BANK')
    initial_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.account_name} ({self.account_type})"

# =========================================================================
# B. CORE OPERATIONAL TABLES
# =========================================================================

# --- 6. Trip (Added Client FK and calculation logic) ---
class Trip(models.Model):
    trip_id = models.CharField(
        max_length=15, unique=True, blank=True, editable=False, verbose_name="Trip ID"
    )
    date = models.DateField()
    
    # Foreign Keys
    vehicle = models.ForeignKey('management.Vehicle', on_delete=models.PROTECT)
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT)
    
    # Client FK (Consignor)
    client = models.ForeignKey(
        PartyMaster, 
        on_delete=models.PROTECT, 
        limit_choices_to={'party_type': 'CLIENT'},
        related_name='trips_as_client',
        verbose_name="Client (Consignor)"
    )
    
    # Transporter FK (Carrier)
    transporter = models.ForeignKey(
        PartyMaster, 
        on_delete=models.PROTECT,
        limit_choices_to={'party_type': 'TRANSPORTER'},
        related_name='trips_as_transporter',
        verbose_name="Transporter (Carrier)"
    )
    
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    
    # Revenue Fields
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Calculated Fields
    total_freight = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False
    )
    commission_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False
    )
    orai_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False
    )

    # Other Financial
    halting = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    advance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Status
    status = models.CharField(
        max_length=20, choices=TRIP_STATUS_CHOICES, default='PENDING'
    )

    
    def generate_trip_id(self):
        """Generates a sequential Trip ID: TRP-0001, TRP-0002, etc."""
        last_id = Trip.objects.all().aggregate(Max('trip_id'))['trip_id__max']
        
        if last_id:
            try:
                # Safely attempt to parse the number part (e.g., 'TRP-0001' -> 1)
                last_number = int(last_id.split('-')[1])
                new_number = last_number + 1
            except (IndexError, ValueError):
                # Fallback if the format is unexpected
                new_number = 1
        else:
            new_number = 1
            
        return f"TRP-{new_number:04d}"

    def save(self, *args, **kwargs):
        # 1. Generate ID on initial creation
        if not self.trip_id:
            self.trip_id = self.generate_trip_id()

        # 2. Calculate Total Freight
        self.total_freight = self.rate * self.weight

        # 3. Calculate Commission and Orai from TransporterMaster
        if self.transporter:
            # Get the Decimal value from the PartyMaster instance
            commission_rate = self.transporter.commission_rate
            orai_charge = self.transporter.orai_charge
            
            # Calculations
            rate_percentage = commission_rate / Decimal(100)
            self.commission_amount = self.total_freight * rate_percentage
            self.orai_amount = orai_charge
        
        # 4. NEW: Calculate Advance as 80% of Total Freight
        if self.advance == Decimal('0.00'):
             self.advance = self.total_freight * Decimal('0.80')

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.trip_id}: {self.origin} to {self.destination}"
    

# --- 7. Trip Expense (Automatic Transaction Logic Included) ---
class TripExpense(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    date = models.DateField()
    
    # Link to cost category
    expense_category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    
    # Link to payment method (AccountMaster)
    paid_via_account = models.ForeignKey(
        'AccountMaster',
        on_delete=models.SET_NULL,
        verbose_name="Paid Via Account",
        null=True,
        blank=True
    )
    
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    bill_no = models.CharField(max_length=50, blank=True, null=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None # Check if object is being created for the first time
        
        # Save the TripExpense object first to get the PK
        super().save(*args, **kwargs)
        
        # --- AUTOMATIC TRANSACTION LOGIC ---
        # 1. Create a corresponding withdrawal in AccountTransaction ONLY for true expenses paid via an account.
        if is_new and self.paid_via_account:
            # We must use AccountTransaction here, assuming it's defined later in the file
            # If AccountTransaction is not defined yet, this will cause an error on import.
            # (Assuming you will place the definition for AccountTransaction later, as in your original file)
            # Find a way to handle circular imports or use 'post_save' signal in Django for better practice.
            # Keeping it here for structural integrity based on your original save() logic:
            AccountTransaction.objects.create(
                date=self.date,
                description=f"EXP: {self.expense_category.name} for {self.trip.trip_id} - {self.description}",
                from_account=self.paid_via_account,
                withdrawal=self.amount,
                related_trip=self.trip,
            )

    def __str__(self):
        return f"Exp for {self.trip.trip_id} - {self.expense_category.name}"


# --- 8. Maintenance Expense (Tracks Credit/Debit) ---
class MaintenanceExpense(models.Model):
    date = models.DateField()
    
    # Links to vehicle and the workshop
    vehicle = models.ForeignKey('management.Vehicle', on_delete=models.PROTECT)
    workshop = models.ForeignKey(
        PartyMaster, 
        on_delete=models.PROTECT, 
        limit_choices_to={'party_type__in': ['WORKSHOP', 'OTHER']},
        verbose_name="Workshop/Vendor"
    )
    
    expense_category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    
    description = models.CharField(max_length=255)
    shop = models.CharField(max_length=100, blank=True, null=True, verbose_name="Workshop Location/Name")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total Bill Amount")
    
    # Credit Tracking Fields
    is_paid = models.BooleanField(default=False, verbose_name="Payment Status")
    payment_date = models.DateField(blank=True, null=True, verbose_name="Date Paid")
    
    # How was the bill settled? (Filled only after payment)
    paid_via_account = models.ForeignKey(
        AccountMaster, on_delete=models.SET_NULL, blank=True, null=True, 
        related_name='maintenance_payments', verbose_name="Paid From Account"
    )

    def __str__(self):
        return f"Maint: {self.vehicle.vehicle_no} - {self.workshop.name}"


# --- 9. Docket Table ---
class DocketTable(models.Model):
    # Links
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT)
    # The limit_choices_to isn't necessary here if the FK is defined in Trip
    transporter = models.ForeignKey(
        PartyMaster, 
        on_delete=models.PROTECT, 
        limit_choices_to={'party_type': 'TRANSPORTER'} # Defensive Filter
    )

    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    docket_no = models.CharField(max_length=50, unique=True)
    send_date = models.DateField(verbose_name="Docket Sent Date")
    
    # Tracking Status
    challan_received = models.BooleanField(default=False, verbose_name="Challan/Docket Received")
    received_date = models.DateField(blank=True, null=True, verbose_name="Received Date")

    def __str__(self):
        return self.docket_no


# --- 10. Account Transaction (Financial Ledger) ---
class AccountTransaction(models.Model):
    date = models.DateField()
    description = models.CharField(max_length=255)
    
    # Transfer details
    from_account = models.ForeignKey(
        AccountMaster, on_delete=models.PROTECT, related_name='withdrawals', 
        verbose_name="From Account"
    )
    to_account = models.ForeignKey(
        AccountMaster, on_delete=models.PROTECT, related_name='deposits', 
        blank=True, null=True, verbose_name="To Account (For Transfers/Deposits)"
    )
    
    # Amount Details
    withdrawal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    deposit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Optional links for automated payments
    related_trip = models.ForeignKey('Trip', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='advance_receipts'
    )
    related_maintenance = models.ForeignKey(
        MaintenanceExpense, on_delete=models.SET_NULL, blank=True, null=True, 
        verbose_name="Related Maintenance Payment"
    )

    def clean(self):
        if self.withdrawal > 0 and self.deposit > 0:
            raise ValidationError(
                _('A single transaction cannot have both a Deposit and a Withdrawal.')
            )
        
        if self.withdrawal == 0 and self.deposit == 0:
            raise ValidationError(
                _('Transaction must have a Deposit or a Withdrawal amount.')
            )
        
        # Logic for Transfers/Deposits/Withdrawals
        is_withdrawal = self.withdrawal > 0
        is_deposit = self.deposit > 0
        
        if is_withdrawal and not self.from_account:
            raise ValidationError(_('A Withdrawal requires a "From Account".'))

        if is_deposit and not self.to_account:
            # Allow a withdrawal from one to be a deposit into another, or a direct deposit into 'to_account'.
            # If deposit > 0, we MUST have a receiving account.
            raise ValidationError(_('A Deposit requires a "To Account".'))


    def save(self, *args, **kwargs):
        # Validate before saving
        self.full_clean() # Use full_clean() to call clean() and validate model fields
        
        super().save(*args, **kwargs)
        
        # --- AUTOMATIC DEBT CLOSURE LOGIC ---
        # If this transaction is related to a Maintenance Expense and that expense is not yet paid, mark it as paid.
        if self.related_maintenance and not self.related_maintenance.is_paid:
            self.related_maintenance.is_paid = True
            self.related_maintenance.payment_date = self.date
            # Assuming the payment came FROM the account specified in the transaction
            self.related_maintenance.paid_via_account = self.from_account 
            self.related_maintenance.save()

    def __str__(self):
        if self.withdrawal > 0 and self.to_account:
            return f"Transfer: {self.withdrawal} from {self.from_account} to {self.to_account}"
        elif self.withdrawal > 0:
            return f"Withdrawal: {self.withdrawal} from {self.from_account}"
        else:
            return f"Deposit: {self.deposit} to {self.to_account}"
        
    related_maintenance_expense = models.ForeignKey(
        'MaintenanceExpense', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='transactions_from_maintenance',
        help_text="Links to the source Maintenance Expense."
    )
    
    related_trip_expense = models.ForeignKey(
        'TripExpense', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='transactions_from_trip_expense',
        help_text="Links to the source Trip Expense."
    )
    
    related_trip = models.ForeignKey(
        'Trip', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='transactions_from_trip',
        help_text="Links to the source Trip (e.g., for receipts)."
    )

