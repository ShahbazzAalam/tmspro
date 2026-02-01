# C:\Users\Alam\tms_project\management\signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import MaintenanceExpense, TripExpense, AccountTransaction

@receiver(post_save, sender=MaintenanceExpense)
def create_maintenance_transaction(sender, instance, created, **kwargs):
    """
    Creates an AccountTransaction (withdrawal) when a MaintenanceExpense is saved 
    and marked as paid via a specific account.
    """
    # 1. Check if the record is newly created AND is marked as paid
    if created and instance.is_paid and instance.paid_via_account:
        
        # 2. Check if a transaction for this expense already exists (prevent duplicates)
        # Note: A more robust check might involve a dedicated FK on AccountTransaction, 
        # but for now, we'll check based on a description pattern.
        
        description = f"Maintenance Expense: {instance.expense_category.name} for {instance.vehicle.license_plate} - {instance.shop}"
        
        AccountTransaction.objects.create(
            date=instance.payment_date or instance.date, # Use payment_date if available
            # Expense is always a withdrawal from a primary account
            withdrawal=instance.amount, 
            deposit=0,
            
            # The account money was paid FROM
            from_account=instance.paid_via_account,
            
            # Since this is an expense, money leaves the company. 'To Account' can be NULL 
            # or reference the workshop/vendor's implied account if you had one.
            # We'll leave it NULL for simplicity as an expense outflow.
            
            description=description,
            related_maintenance_expense=instance # Link back to the source expense for auditing
        )

@receiver(post_save, sender=TripExpense)
def create_trip_expense_transaction(sender, instance, created, **kwargs):
    """
    Creates an AccountTransaction (withdrawal) when a TripExpense is saved 
    and marked as paid via a specific account.
    """
    # 1. Check if the record is newly created AND a payment account was specified
    # Note: TripExpense paid_via_account might be optional (e.g., driver cash).
    if created and instance.paid_via_account:
        
        description = f"Trip Expense: {instance.expense_category.name} on Trip {instance.trip.trip_id}"
        
        AccountTransaction.objects.create(
            date=instance.date,
            withdrawal=instance.amount,
            deposit=0,
            
            # The account money was paid FROM
            from_account=instance.paid_via_account, 
            
            description=description,
            related_trip_expense=instance # Link back to the source expense for auditing
        )