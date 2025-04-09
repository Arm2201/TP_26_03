from django.shortcuts import render, redirect, get_object_or_404
from .forms import CustomUserCreationForm, EditProfileForm
from django.contrib.auth.decorators import login_required  # For protecting views so only logged-in users can access
from .models import CustomUser, Payment  # Import your models
from django.http import HttpResponseForbidden  # Optional, for handling HTTP responses
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from decimal import Decimal
from django.db import IntegrityError
from django.db.models import Sum
from datetime import datetime
from .models import TopUp


@login_required
def edit_profile(request):
    if request.method == "POST":
        form = EditProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('student_dashboard')  # Redirect to the dashboard
    else:
        form = EditProfileForm(instance=request.user)

    return render(request, 'payments/edit_profile.html', {'form': form})

def home(request):
    return render(request, 'payments/home.html')

from django.contrib.auth import authenticate  # Import this

def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)  # Authenticate user

            if user:
                if not user.is_active:  # Check if user is active
                    messages.error(request, "Your account is inactive.")
                    return redirect('login')

                if not user.is_approved:  # Block unapproved users
                    messages.error(request, "Your account is pending approval from the admin.")
                    return redirect('login')

                login(request, user)  # Log the user in
                
                if user.role == 'student':
                    return redirect('student_dashboard')
                elif user.role == 'store':
                    return redirect('store_dashboard')
                elif user.role == 'teacher':
                    return redirect('student_dashboard')
                elif user.role == 'super_admin':
                    return redirect('admin_dashboard')
            else:
                messages.error(request, "Invalid username or password.")  # Show message if authentication fails
                return redirect('login')
        else:
            messages.error(request, "Invalid login credentials. Please try again.")
            return redirect('login')

    else:
        form = AuthenticationForm()
    
    return render(request, 'payments/login.html', {'form': form})

def get_dashboard_redirect(user):
    if user.role == 'student':
        return 'student_dashboard'
    elif user.role == 'store':
        return 'store_dashboard'
    elif user.role == 'teacher':
        return 'student_dashboard'
    elif user.role == 'super_admin':
        return 'admin_dashboard'
    return 'home'



def custom_logout(request):
    logout(request)  # This logs out the user
    return redirect('login')  # Redirect to the login page (or homepage if you prefer)

def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_approved = False  # New users need approval
            user.save()
            messages.info(request, "Registration successful! Wait for admin approval.")
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'payments/register.html', {'form': form})


@login_required
def student_dashboard(request):
    if request.user.role != 'student':
        return HttpResponseForbidden("You are not authorized to view this page.")
    
    # Fetch the student's payment history
    payments = request.user.payments.all()
    
    return render(request, 'payments/student_dashboard.html', {
        'payments': payments,
        'balance': request.user.balance  # Display the balance
    })

@login_required
def store_dashboard(request):
    if request.user.role != 'store':
        return HttpResponseForbidden("You are not authorized to view this page.")
    
    # Get the start and end date from the GET request, if provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Build the query to filter payments based on the date range
    payment_filter = {}
    if start_date:
        payment_filter['payment_date__gte'] = datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        payment_filter['payment_date__lte'] = datetime.strptime(end_date, '%Y-%m-%d')

    # Fetch payments related to the store with the optional date filter
    store_payments = Payment.objects.filter(store=request.user, **payment_filter)
    
    # Exclude 'top_up' payments from the total sales calculation
    store_payments_without_top_up = store_payments.exclude(payment_type='top_up')
    
    # Calculate the total sales (sum of payment amounts excluding top-ups)
    total_sales = store_payments_without_top_up.aggregate(total=Sum('amount'))['total'] or 0

    # Pass the data to the template
    return render(request, 'payments/store_dashboard.html', {
        'store_payments': store_payments,
        'total_sales': total_sales
    })

@login_required
def admin_dashboard(request):
    if request.user.role != 'super_admin':
        return HttpResponseForbidden("You are not authorized to view this page.")

    # Get approved users
    students = CustomUser.objects.filter(role='student', is_approved=True)
    stores = CustomUser.objects.filter(role='store', is_approved=True)
    teachers = CustomUser.objects.filter(role='teacher', is_approved=True)

    # Get pending users
    pending_users = CustomUser.objects.filter(is_approved=False)

    return render(request, 'payments/admin_dashboard.html', {
        'students': students,
        'stores': stores,
        'teachers':teachers,
        'pending_users': pending_users
    })

@login_required
def approve_user(request, user_id):
    if request.user.role != 'super_admin':
        return HttpResponseForbidden("You are not authorized to approve users.")

    user = get_object_or_404(CustomUser, id=user_id)
    user.is_approved = True
    user.save()
    messages.success(request, f"{user.username} has been approved!")
    
    return redirect('admin_dashboard')

@login_required
def process_payment(request):
    if request.method == 'POST':
        # Get data from the form submission
        student_id = request.POST.get('user_id')  # Update this to match the HTML field name
        amount = Decimal(request.POST.get('amount'))  # Ensure the amount is decimal
        payment_type = request.POST.get('payment_type')

        try:
            # Retrieve the student object with the specified ID and role='student'
            student = CustomUser.objects.get(id=student_id, role='student')

            # Handle top-up payments
            if payment_type == 'top_up':
                if amount <= 0:
                    messages.error(request, "Amount must be greater than zero.")
                    return redirect('store_dashboard')

                # Top-up the student's balance
                student.balance += amount
                student.save()

                # Record the top-up payment in the Payment model
                Payment.objects.create(
                    user=student,
                    amount=amount,
                    payment_type='top_up',
                    store=request.user  # Associate with the store user who processed the payment
                )

                messages.success(request, f"{student.username}'s account topped up successfully!")

            # Handle purchase payments (deduct from student's balance)
            elif payment_type == 'purchase':
                if amount <= 0:
                    messages.error(request, "Amount must be greater than zero.")
                    return redirect('store_dashboard')

                # Check if the student has enough balance for the purchase
                if student.balance >= amount:
                    student.balance -= amount
                    student.save()

                    # Record the purchase payment in the Payment model
                    Payment.objects.create(
                        user=student,
                        amount=amount,
                        payment_type='purchase',
                        store=request.user  # Associate with the store user who processed the payment
                    )

                    messages.success(request, f"{student.username}'s purchase processed successfully!")
                else:
                    messages.error(request, "Insufficient balance for purchase.")

            else:
                messages.error(request, "Unsupported payment type.")
        
        except CustomUser.DoesNotExist:
            messages.error(request, "Student not found.")
        except IntegrityError:
            messages.error(request, "An error occurred while processing the payment.")

        # After processing the payment, redirect to the store dashboard
        return redirect('store_dashboard')
    
    # Handle GET requests: Fetch the list of students to display in the form
    students = CustomUser.objects.filter(role='student')  # Fetch all students with 'student' role

    return render(request, 'payments/process_payment.html', {'students': students})

@login_required
def sales_report(request):
    if request.user.role != 'store':
        return HttpResponseForbidden("You are not authorized to view this page.")
    
    store_payments = Payment.objects.filter(store=request.user)
    
    return render(request, 'payments/sales_report.html', {
        'store_payments': store_payments
    })

@login_required
def update_settings(request):
    if request.user.role != 'super_admin':
        return HttpResponseForbidden("You are not authorized to view this page.")
    
    # Add logic to update settings, such as system-wide parameters
    return render(request, 'payments/update_settings.html')

@login_required
def edit_user(request, user_id):
    if request.user.role != 'super_admin':
        return HttpResponseForbidden("You are not authorized to view this page.")

    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard')
    else:
        form = CustomUserCreationForm(instance=user)

    return render(request, 'payments/edit_user.html', {'form': form, 'user': user})

# View for deleting a user
@login_required
def delete_user(request, user_id):
    if request.user.role != 'super_admin':
        return HttpResponseForbidden("You are not authorized to view this page.")

    user = get_object_or_404(CustomUser, id=user_id)
    user.delete()

    return redirect('admin_dashboard')

def student_dashboard(request):
    balance = 100  # Example balance, replace with actual logic
    return render(request, 'payments/student_dashboard.html', {'balance': balance})

@login_required
def purchase_history(request):
    payments = Payment.objects.filter(user=request.user, payment_type='purchase').order_by('-payment_date')
    return render(request, 'payments/purchase_history.html', {'payments': payments})



@login_required
def top_up_history(request):
    top_up_records = TopUp.objects.filter(user=request.user).order_by('-date')
    return render(request, 'payments/top_up_history.html', {'top_up_records': top_up_records})
