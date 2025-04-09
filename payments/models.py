from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.conf import settings  # Import settings to access AUTH_USER_MODEL

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('store', 'Store'),
        ('teacher', 'Teacher'),
        ('super_admin', 'Super Admin'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    is_approved = models.BooleanField(default=False)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # For students only
    profile_image = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.png')
    ID = models.CharField(max_length=255, unique=True)  # New field

    # Add unique related names to avoid conflicts
    groups = models.ManyToManyField(
        Group,
        related_name='customuser_groups',  # Custom related name
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_permissions',  # Custom related name
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    # Override the save method
    def save(self, *args, **kwargs):
        if self.role == 'super_admin':  # Auto-approve admins
            self.is_approved = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

class Payment(models.Model):
    PAYMENT_TYPES = [
        ('top_up', 'Top-Up'),
        ('purchase', 'Purchase'),
        ('refund', 'Refund'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    store = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='store_payments',
        null=True, blank=True  # Relevant for store transactions
    )

    def __str__(self):
        return f"{self.user.username} - {self.payment_type} - ${self.amount}"

# top up
class TopUp(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Use settings.AUTH_USER_MODEL
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Amount topped up
    date = models.DateTimeField(auto_now_add=True)  # Automatically set the date when the record is created
    status = models.CharField(max_length=50, choices=[('Pending', 'Pending'), ('Completed', 'Completed')])  # Top-up status

    def __str__(self):
        return f"Top-up of {self.amount} by {self.user} on {self.date}"
