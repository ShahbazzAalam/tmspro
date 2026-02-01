# management/views.py (COMPLETE & FINAL FILE)

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.urls import reverse
from decimal import Decimal
from datetime import date
from django.views.decorators.http import require_POST
from .models import (
    Trip, TripExpense, Vehicle, Driver, PartyMaster,
    ExpenseCategory, MaintenanceExpense,
    AccountMaster, AccountTransaction
)

from .forms import (
    TripForm, TripExpenseForm, MaintenanceExpenseForm,
    ExpenseCategoryForm, AccountMasterForm, AdvanceReceiptForm, 
    VehicleForm, PartyMasterForm, AccountTransferForm, DriverForm,
    TripSettlementForm  # Make sure this is in your forms.py!
)

# ----------------------------------------------------------------------
# 1. Trip List Dashboard View
# ----------------------------------------------------------------------
def trip_list(request):
    """Dashboard View (Lists all trips)"""
    trips = Trip.objects.all().select_related('vehicle', 'driver', 'transporter').order_by('-date')
    context = {
        'trips': trips,
        'title': 'Trip List & Dashboard'
    }
    return render(request, 'management/trip_list.html', context)

# ----------------------------------------------------------------------
# 2. Create/Update Trip Views
# ----------------------------------------------------------------------
def trip_create(request):
    """View to create a new trip"""
    if request.method == 'POST':
        form = TripForm(request.POST)
        if form.is_valid():
            trip = form.save()
            return redirect('trip_detail', trip_id=trip.trip_id) 
    else:
        form = TripForm()
        
    context = {
        'form': form,
        'title': 'Create New Trip'
    }
    return render(request, 'management/trip_form.html', context)

def trip_update(request, trip_id):
    """Updates an existing Trip record."""
    # Note: Using trip_id from the URL to fetch the Trip object
    trip = get_object_or_404(Trip, trip_id=trip_id)

    if request.method == 'POST':
        # Initialize form with POST data and the existing instance
        form = TripForm(request.POST, instance=trip)
        if form.is_valid():
            # The save() method will trigger the automatic 80% calculation 
            # ONLY if the user hasn't touched the 'advance' field (i.e., it's 0.00).
            # If the user enters a manual amount, that manual amount will be saved.
            form.save() 
            messages.success(request, f"Trip {trip.trip_id} updated successfully.")
            return redirect('trip_detail', trip_id=trip.trip_id)
    else:
        # Initialize form with the existing instance data
        form = TripForm(instance=trip)

    context = {
        'form': form,
        'trip': trip,
        'title': f'Update Trip: {trip.trip_id}'
    }
    # This view typically reuses the trip_create template
    return render(request, 'management/trip_create_update.html', context)
# ----------------------------------------------------------------------
# 3. Trip Detail & Expense Management View
# ----------------------------------------------------------------------
def trip_detail(request, trip_id):
    """View to display trip details, expenses, and P&L."""
    trip = get_object_or_404(Trip, trip_id=trip_id)
    trip_expenses = TripExpense.objects.filter(trip=trip).order_by('date')
    
    # --- 1. NEW: Fetch Advance Receipts ---
    advance_receipts = trip.transactions_from_trip.filter(deposit__gt=0).order_by('date')
    total_advance_received = advance_receipts.aggregate(Sum('deposit'))['deposit__sum'] or Decimal('0.00')
    total_freight = trip.total_freight or Decimal('0.00')

    # Percentage of Total Freight for the Agreed Advance Amount
    advance_agreed_percent = Decimal('0.00')
    if total_freight > 0:
        advance_agreed_percent = (trip.advance / total_freight) * 100
        
    # Percentage of Total Freight for the Advance Amount ALREADY RECEIVED
    received_percent = Decimal('0.00')
    if total_freight > 0:
        received_percent = (total_advance_received / total_freight) * 100

    # --- 2. EXPENSE CATEGORY & HALTING LOGIC ---
    halting_amount = Decimal(0)
    deductible_expenses_query = trip_expenses 
    
    try:
        halting_category = ExpenseCategory.objects.get(name__iexact='Halting Charges')
        halting_sum_result = trip_expenses.filter(expense_category=halting_category).aggregate(Sum('amount'))
        halting_amount = halting_sum_result['amount__sum'] or Decimal(0)
        deductible_expenses_query = trip_expenses.exclude(expense_category=halting_category)
    except ExpenseCategory.DoesNotExist:
        pass 
        
    # --- 3. CALCULATE FINAL FINANCIAL FIGURES ---
    total_revenue = trip.total_freight + halting_amount
    deductible_expenses_sum = deductible_expenses_query.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    all_expenses_sum = deductible_expenses_sum 

    profit_loss = (
        total_revenue - 
        trip.commission_amount - 
        trip.orai_amount - 
        deductible_expenses_sum 
    )

    # --- 4. SYNTHETIC EXPENSES FOR DISPLAY ---
    SyntheticAttr = type('obj', (object,), {'name': 'N/A', 'account_name': 'N/A'})
    display_expenses = list(trip_expenses) 

    if trip.commission_amount > 0:
        commission_category = SyntheticAttr()
        commission_category.name = 'Transporter Commission'
        commission_account = SyntheticAttr()
        commission_account.account_name = 'N/A'
        display_expenses.append({
            'date': trip.date,
            'expense_category': commission_category,
            'description': 'Agent Commission (Pre-calculated)',
            'amount': trip.commission_amount,
            'paid_via_account': commission_account,
            'is_synthetic': True, 
        })

    if trip.orai_amount > 0:
        orai_category = SyntheticAttr()
        orai_category.name = 'Orai Charges'
        orai_account = SyntheticAttr()
        orai_account.account_name = 'N/A'
        display_expenses.append({
            'date': trip.date,
            'expense_category': orai_category,
            'description': 'Fixed Orai Deduction (Pre-calculated)',
            'amount': trip.orai_amount,
            'paid_via_account': orai_account,
            'is_synthetic': True,
        })
    
    display_expenses.sort(key=lambda x: x['date'] if isinstance(x, dict) else x.date)

    # --- 5. HANDLE EXPENSE FORM SUBMISSION ---
    if request.method == 'POST':
        if 'expense_submit' in request.POST:
            expense_form = TripExpenseForm(request.POST)
            if expense_form.is_valid():
                expense = expense_form.save(commit=False)
                expense.trip = trip 
                expense.save()
                messages.success(request, f"Expense '{expense.expense_category.name}' recorded successfully.")
                return redirect('trip_detail', trip_id=trip.trip_id)
    else:
        expense_form = TripExpenseForm()

    print(f"DEBUG: Total Advance Received: {total_advance_received}")
    print(f"DEBUG: Calculated Percentage: {total_advance_received}")

    context = {
        'trip': trip,
        'trip_expenses': display_expenses,
        'advance_receipts': advance_receipts,
        'total_advance_received': total_advance_received,
        'advance_agreed_percent': advance_agreed_percent, # <-- ADD THIS
        'received_percent': received_percent,
        'total_revenue': total_revenue,
        'total_expenses': all_expenses_sum,
        'profit_loss': profit_loss,
        'expense_form': expense_form,
        'halting_amount': halting_amount,
        'title': f'Details for Trip: {trip.trip_id}'
    }
    return render(request, 'management/trip_detail.html', context)

# ----------------------------------------------------------------------
# 4. Record Advance Receipt View
# ----------------------------------------------------------------------
# In management/views.py

def trip_record_advance(request, trip_id):
    trip = get_object_or_404(Trip, trip_id=trip_id)
    
    # 1. Fetch Advance Transactions
    # We use the related_name 'transactions_from_trip' defined in models.py
    advance_transactions = trip.transactions_from_trip.filter(deposit__gt=0).order_by('-date')
    
    # 2. Calculate Total Receipts
    current_receipts = advance_transactions.aggregate(Sum('deposit'))['deposit__sum'] or Decimal('0.00')
    
    # 3. Calculate Percentage Values (NEW)
    total_freight = trip.total_freight or Decimal('0.00')
    
    # Calculate Advance Agreed Percentage
    advance_agreed_percent = Decimal('0.00')
    if total_freight > 0:
        # Calculates what percentage of total freight the agreed advance is
        advance_agreed_percent = (trip.advance / total_freight) * 100

    # Calculate Received Amount Percentage
    received_percent = Decimal('0.00')
    if total_freight > 0:
        # Calculates what percentage of total freight has been received so far
        received_percent = (current_receipts / total_freight) * 100
        
    if request.method == 'POST':
        form = AdvanceReceiptForm(request.POST)
        if form.is_valid():
            advance_date = form.cleaned_data['date']
            account = form.cleaned_data['account']
            actual_amount_received = form.cleaned_data['amount'] 

            AccountTransaction.objects.create(
                date=advance_date,
                description=f"Advance Receipt for Trip {trip.trip_id}",
                to_account=account, 
                deposit=actual_amount_received,
                related_trip=trip, 
                from_account=account # Assuming advance comes from the company or client to our account
            )

            messages.success(request, f"Advance receipt of ₹{actual_amount_received} recorded.")
            return redirect('trip_detail', trip_id=trip.trip_id)
    else:
        # FIXED: Initialize the form with 0.00 for user to input
        form = AdvanceReceiptForm(initial={'amount': 0.00}) 

    context = {
        'form': form,
        'trip': trip,
        'total_advance_received': current_receipts,
        'advance_transactions': advance_transactions,
        'advance_agreed_percent': advance_agreed_percent, # <-- Passed to template
        'received_percent': received_percent,             # <-- Passed to template
        'title': f'Record Advance Receipt for Trip {trip.trip_id}'
    }
    return render(request, 'management/advance_receipt_form.html', context)
# ----------------------------------------------------------------------
# 5. Trip Final Settlement View (NEW)
# ----------------------------------------------------------------------
def trip_final_settlement(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    
    # 1. Calculate Financials
    total_advance = trip.transactions_from_trip.filter(deposit__gt=0).aggregate(Sum('deposit'))['deposit__sum'] or Decimal('0.00')
    balance_due = trip.total_freight - total_advance

    if request.method == 'POST':
        form = TripSettlementForm(request.POST)
        if form.is_valid():
            received_amount = form.cleaned_data['received_amount']
            shortage = form.cleaned_data['shortage_damage']
            pay_date = form.cleaned_data['payment_date']
            account = form.cleaned_data['account']
            remarks = form.cleaned_data['remarks']

            if received_amount > (balance_due - shortage):
                messages.warning(request, "Warning: You are receiving more than the calculated balance.")

            if received_amount > 0:
                AccountTransaction.objects.create(
                    date=pay_date,
                    from_account=account,
                    to_account=account,
                    deposit=received_amount,
                    related_trip=trip,
                    description=f"Settlement for Trip {trip.trip_id}. (Shortage: {shortage}). {remarks}"
                )

            trip.status = 'COMPLETED'
            trip.save()

            messages.success(request, f"Trip {trip.trip_id} settled and marked as COMPLETED.")
            return redirect('trip_detail', trip_id=trip.trip_id)
    else:
        form = TripSettlementForm(initial={
            'total_freight': trip.total_freight,
            'advance_received': total_advance,
            'balance_due': balance_due,
            'received_amount': balance_due,
        })

    context = {
        'trip': trip,
        'form': form,
        'title': f'Settlement: {trip.trip_id}'
    }
    return render(request, 'management/trip_final_settlement.html', context)

# ----------------------------------------------------------------------
# 6. Account Management Views
# ----------------------------------------------------------------------
def account_list(request):
    accounts = AccountMaster.objects.all().order_by('account_name')
    context = {'accounts': accounts, 'title': 'Account List & Balances'}
    return render(request, 'management/account_list.html', context)

def account_create(request):
    if request.method == 'POST':
        form = AccountMasterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Account '{form.cleaned_data['account_name']}' created.")
            return redirect('account_list')
    else:
        form = AccountMasterForm()
    context = {'form': form, 'title': 'Create New Account'}
    return render(request, 'management/account_form.html', context)

def account_update(request, account_id):
    account = get_object_or_404(AccountMaster, pk=account_id)
    if request.method == 'POST':
        form = AccountMasterForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            return redirect('account_list')
    else:
        form = AccountMasterForm(instance=account)
    context = {'form': form, 'account': account, 'title': f'Edit Account: {account.account_name}'}
    return render(request, 'management/account_form.html', context)

def account_detail(request, account_id):
    account = get_object_or_404(AccountMaster, pk=account_id)
    all_transactions = AccountTransaction.objects.filter(
        Q(from_account=account) | Q(to_account=account)
    ).order_by('date', 'pk')
    
    running_balance = account.initial_balance
    ledger_entries = []
    
    for transaction in all_transactions:
        deposit = transaction.deposit
        withdrawal = transaction.withdrawal
        
        if transaction.from_account == account and transaction.to_account != account:
            # Money leaving this account
            running_balance -= withdrawal
        elif transaction.to_account == account:
            # Money entering this account
            running_balance += deposit
            
        ledger_entries.append({
            'date': transaction.date,
            'description': transaction.description,
            'credit': deposit if transaction.to_account == account else 0,
            'debit': withdrawal if transaction.from_account == account and transaction.to_account != account else 0,
            'related_trip': transaction.related_trip,
            'current_balance': running_balance
        })

    context = {
        'account': account,
        'ledger_entries': ledger_entries,
        'final_balance': running_balance,
        'title': f'Ledger for {account.account_name}'
    }
    return render(request, 'management/account_detail.html', context)

def account_transfer(request):
    if request.method == 'POST':
        form = AccountTransferForm(request.POST)
        if form.is_valid():
            from_account = form.cleaned_data['from_account']
            to_account = form.cleaned_data['to_account']
            amount = form.cleaned_data['withdrawal'] # Using withdrawal field for amount
            date = form.cleaned_data['date']
            description = form.cleaned_data['description']
            
            AccountTransaction.objects.create(
                date=date,
                description=f"Transfer OUT to {to_account.account_name}: {description}",
                from_account=from_account,
                withdrawal=amount,
                to_account=to_account,
            )
            
            AccountTransaction.objects.create(
                date=date,
                description=f"Transfer IN from {from_account.account_name}: {description}",
                from_account=from_account,
                deposit=amount,
                to_account=to_account,
            )
            
            messages.success(request, "Transfer successful.")
            return redirect('account_list')
    else:
        form = AccountTransferForm()
    context = {'form': form, 'title': 'Fund Transfer'}
    return render(request, 'management/account_transfer_form.html', context)

# ----------------------------------------------------------------------
# 7. Party Master Views
# ----------------------------------------------------------------------
def party_list(request):
    parties = PartyMaster.objects.all().order_by('party_type', 'name')
    context = {'parties': parties, 'title': 'Party Master'}
    return render(request, 'management/party_list.html', context)

def party_create(request):
    if request.method == 'POST':
        form = PartyMasterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('party_list')
    else:
        form = PartyMasterForm()
    context = {'form': form, 'title': 'Create New Party'}
    return render(request, 'management/party_form.html', context)

def party_detail(request, pk):
    party = get_object_or_404(PartyMaster, pk=pk)
    associated_trips = Trip.objects.filter(Q(client=party) | Q(transporter=party)).order_by('-date')
    context = {'party': party, 'associated_trips': associated_trips, 'title': party.name}
    return render(request, 'management/party_detail.html', context)

def party_update(request, pk):
    party = get_object_or_404(PartyMaster, pk=pk)
    if request.method == 'POST':
        form = PartyMasterForm(request.POST, instance=party)
        if form.is_valid():
            form.save()
            return redirect('party_detail', pk=party.pk)
    else:
        form = PartyMasterForm(instance=party)
    context = {'form': form, 'party': party, 'title': f'Edit {party.name}'}
    return render(request, 'management/party_form.html', context)

def party_delete(request, pk):
    party = get_object_or_404(PartyMaster, pk=pk)
    is_linked = Trip.objects.filter(Q(client=party) | Q(transporter=party)).exists()
    if request.method == 'POST':
        if not is_linked:
            party.delete()
            return redirect('party_list')
    context = {'party': party, 'is_linked': is_linked, 'title': f'Delete {party.name}'}
    return render(request, 'management/party_confirm_delete.html', context)

# ----------------------------------------------------------------------
# 8. Vehicle & Driver Views
# ----------------------------------------------------------------------
def vehicle_list(request):
    vehicles = Vehicle.objects.all().order_by('vehicle_no')
    context = {'vehicles': vehicles, 'title': 'Vehicle Master List'}
    return render(request, 'management/vehicle_list.html', context)

def vehicle_create(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('vehicle_list')
    else:
        form = VehicleForm()
    context = {'form': form, 'title': 'Add New Vehicle'}
    return render(request, 'management/vehicle_form.html', context)

def vehicle_update(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            return redirect('vehicle_list')
    else:
        form = VehicleForm(instance=vehicle)
    context = {'form': form, 'vehicle': vehicle, 'title': f'Update {vehicle.vehicle_no}'}
    return render(request, 'management/vehicle_form.html', context)

def driver_list(request):
    drivers = Driver.objects.all().order_by('driver_id')
    context = {'drivers': drivers, 'title': 'Driver Master List'}
    return render(request, 'management/driver_list.html', context)

def driver_create(request):
    if request.method == 'POST':
        form = DriverForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('driver_list')
    else:
        form = DriverForm()
    context = {'form': form, 'title': 'Create New Driver'}
    return render(request, 'management/driver_form.html', context)

def driver_update(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    form_kwargs = {'instance': driver}
    if request.method == 'POST':
        form = DriverForm(request.POST, **form_kwargs)
        if form.is_valid():
            form.save()
            return redirect('driver_list')
    else:
        form = DriverForm(**form_kwargs)
    form.fields['driver_id'].widget.attrs['readonly'] = 'readonly'
    context = {'form': form, 'driver': driver, 'title': f'Update {driver.name}'}
    return render(request, 'management/driver_form.html', context)

def driver_delete(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        driver.delete()
        return redirect('driver_list')
    context = {'driver': driver, 'title': f'Delete {driver.name}'}
    return render(request, 'management/driver_confirm_delete.html', context)

# ----------------------------------------------------------------------
# 9. Expense Category & Maintenance Views
# ----------------------------------------------------------------------
def expense_category_list(request):
    categories = ExpenseCategory.objects.all().order_by('name')
    context = {'categories': categories, 'title': 'Expense Categories'}
    return render(request, 'management/expense_category_list.html', context)

def expense_category_create(request):
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('expense_category_list')
    else:
        form = ExpenseCategoryForm()
    context = {'form': form, 'title': 'Create New Category'}
    return render(request, 'management/expense_category_form.html', context)

def expense_category_update(request, pk):
    raise Http404("Expense Category Update View Not Implemented Yet.")

def maintenance_expense_list(request):
    expenses = MaintenanceExpense.objects.select_related('vehicle', 'workshop').order_by('-date')
    context = {'expenses': expenses, 'title': 'Vehicle Maintenance History'}
    return render(request, 'management/maintenance_expense_list.html', context)

def maintenance_expense_create(request):
    if request.method == 'POST':
        form = MaintenanceExpenseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('maintenance_expense_list')
    else:
        form = MaintenanceExpenseForm()
    context = {'form': form, 'title': 'Record Maintenance'}
    return render(request, 'management/maintenance_expense_form.html', context)

def trip_expense_create(request, trip_id):
    """
    Handle creation of an expense tied to a specific trip.
    """
    trip = get_object_or_404(Trip, trip_id=trip_id)
    
    if request.method == 'POST':
        form = TripExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.trip = trip  # CRITICAL: Link the expense to the current trip
            expense.save()
            messages.success(request, f"Expense '{expense.expense_category.name}' recorded successfully.")
            return redirect('trip_detail', trip_id=trip.trip_id)
    else:
        form = TripExpenseForm()
    
    context = {
        'form': form,
        'trip': trip,
        'title': f'Record Expense for Trip {trip.trip_id}',
    }
    return render(request, 'management/trip_expense_form.html', context)



@require_POST
def trip_status_revert(request, trip_id):
    """Reverts a trip from 'COMPLETED' back to 'IN_TRANSIT'."""
    
    # 1. CRITICAL: Authentication Check for AJAX
    if not request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Authentication required. Please log in.'}, status=401)
            
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)
        
    try:
        # ... (rest of the revert logic) ...
        trip = get_object_or_404(Trip, trip_id=trip_id)
        trip.status = 'IN_TRANSIT'
        trip.save()
        # ...
        
        return JsonResponse({
            'success': True, 
            'message': f'Trip {trip.trip_id} status reverted to IN-TRANSIT.',
            'new_status_display': 'In-transit',
            'new_status_class': 'bg-warning text-dark'
        })
        
    except Http404:
        return JsonResponse({'success': False, 'message': f'Trip {trip_id} not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Internal Server Error: {str(e)}'}, status=500)
# We need to change the completion view to return the trip_id so the JS knows what to undo.
@require_POST 
def trip_status_complete(request, trip_id):
    """
    Updates the trip status to 'COMPLETED'. 
    Handles AJAX authentication failure by returning 401 JSON instead of redirecting.
    """
    
    # 1. CRITICAL: Check Authentication and AJAX Header
    # If the user is not authenticated AND the request is AJAX, return 401 JSON.
    # This prevents the default Django 302 redirect to the login page (which returns HTML).
    if not request.user.is_authenticated:
        # Check if it's an AJAX request (using the header sent by your JS)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Return JSON with 401 status code
            return JsonResponse({'success': False, 'message': 'Authentication required. Please log in.'}, status=401)
        # If not AJAX, let the @login_required middleware handle the standard redirect
        # NOTE: You can remove the @login_required decorator if you use this check, 
        # but leaving it simplifies handling non-AJAX POSTs.
    
    # Optional: Redundant, but harmless, request type check
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Invalid request type.'}, status=400)
    
    try:
        trip = get_object_or_404(Trip, trip_id=trip_id)
        
        # Actual status change logic
        trip.status = 'COMPLETED'
        trip.save()

        return JsonResponse({
            'success': True, 
            'message': f'Trip {trip.trip_id} successfully marked COMPLETED.',
            'new_status_display': 'Completed',
            'new_status_class': 'bg-success',
            'trip_id': trip.trip_id
        })
        
    except Http404:
        return JsonResponse({'success': False, 'message': f'Trip {trip_id} not found.'}, status=404)
    except Exception as e:
        # Catches any unexpected server error and returns JSON 500
        return JsonResponse({'success': False, 'message': f'Internal Server Error: {str(e)}'}, status=500)