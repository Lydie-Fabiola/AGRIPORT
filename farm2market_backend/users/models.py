from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from .managers import UserManager


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    Based on the users_customuser table from farm2market.sql
    """
    USER_TYPE_CHOICES = [
        ('Farmer', _('Farmer')),
        ('Buyer', _('Buyer')),
        ('Admin', _('Admin')),
    ]

    # Override username to match SQL schema exactly
    username = models.CharField(
        max_length=50,
        unique=True,
        help_text=_('Required. 50 characters or fewer.')
    )

    email = models.EmailField(
        _('email address'),
        max_length=254,
        unique=True,
        help_text=_('Required. Enter a valid email address.')
    )

    phone_number = models.CharField(
        _('phone number'),
        max_length=20,
        help_text=_('Enter phone number with country code.')
    )

    user_type = models.CharField(
        _('user type'),
        max_length=10,
        choices=USER_TYPE_CHOICES,
        help_text=_('Select user type: Farmer, Buyer, or Admin.')
    )

    is_approved = models.BooleanField(
        _('approved'),
        default=False,
        help_text=_('Designates whether this user has been approved by admin.')
    )

    # Additional fields for verification and security
    email_verified = models.BooleanField(
        _('email verified'),
        default=False,
        help_text=_('Designates whether this user has verified their email address.')
    )

    phone_verified = models.BooleanField(
        _('phone verified'),
        default=False,
        help_text=_('Designates whether this user has verified their phone number.')
    )

    failed_login_attempts = models.PositiveIntegerField(
        _('failed login attempts'),
        default=0,
        help_text=_('Number of consecutive failed login attempts.')
    )

    last_failed_login = models.DateTimeField(
        _('last failed login'),
        null=True,
        blank=True,
        help_text=_('Date and time of last failed login attempt.')
    )

    account_locked_until = models.DateTimeField(
        _('account locked until'),
        null=True,
        blank=True,
        help_text=_('Account is locked until this date and time.')
    )
    
    # Use email as the unique identifier for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'user_type', 'phone_number']

    # Custom manager
    objects = UserManager()

    class Meta:
        db_table = 'users_customuser'
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return f"{self.email} ({self.get_user_type_display()})"

    @property
    def full_name(self):
        """Return the full name of the user."""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_farmer(self):
        """Check if user is a farmer."""
        return self.user_type == 'Farmer'

    @property
    def is_buyer(self):
        """Check if user is a buyer."""
        return self.user_type == 'Buyer'

    @property
    def is_admin_user(self):
        """Check if user is an admin."""
        return self.user_type == 'Admin'

    @property
    def is_account_locked(self):
        """Check if account is currently locked."""
        if self.account_locked_until:
            from django.utils import timezone
            return timezone.now() < self.account_locked_until
        return False

    def lock_account(self, duration_minutes=30):
        """Lock the account for specified duration."""
        from django.utils import timezone
        from datetime import timedelta
        self.account_locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save(update_fields=['account_locked_until'])

    def unlock_account(self):
        """Unlock the account."""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['account_locked_until', 'failed_login_attempts'])

    def increment_failed_login(self):
        """Increment failed login attempts."""
        from django.utils import timezone
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()

        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account()

        self.save(update_fields=['failed_login_attempts', 'last_failed_login'])

    def reset_failed_login(self):
        """Reset failed login attempts on successful login."""
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.account_locked_until = None
        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'account_locked_until'])

    def save(self, *args, **kwargs):
        # Auto-generate username from email if not provided
        if not self.username and self.email:
            base_username = self.email.split('@')[0]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            self.username = username
        super().save(*args, **kwargs)


class FarmerProfile(models.Model):
    """
    Farmer-specific profile information
    Based on the farmer_profiles table from farm2market.sql
    """
    farmer = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='farmer_profile',
        limit_choices_to={'user_type': 'farmer'}
    )
    
    location = models.CharField(
        _('location'),
        max_length=100,
        blank=True,
        help_text=_('Farmer\'s location/address.')
    )
    
    trust_badge = models.BooleanField(
        _('trust badge'),
        default=False,
        help_text=_('Indicates if farmer has earned a trust badge.')
    )
    
    # Additional fields for enhanced farmer profile
    farm_size = models.DecimalField(
        _('farm size (hectares)'),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_('Size of the farm in hectares.')
    )

    farming_experience = models.PositiveIntegerField(
        _('farming experience (years)'),
        blank=True,
        null=True,
        help_text=_('Years of farming experience.')
    )

    specialization = models.CharField(
        _('specialization'),
        max_length=200,
        blank=True,
        help_text=_('Main crops or farming specialization.')
    )

    bio = models.TextField(
        _('biography'),
        blank=True,
        help_text=_('Brief description about the farmer.')
    )

    # Farm certification and verification
    is_certified = models.BooleanField(
        _('is certified'),
        default=False,
        help_text=_('Whether the farmer has valid certifications.')
    )

    certification_level = models.CharField(
        _('certification level'),
        max_length=50,
        blank=True,
        choices=[
            ('organic', _('Organic')),
            ('fair_trade', _('Fair Trade')),
            ('gmp', _('Good Manufacturing Practice')),
            ('haccp', _('HACCP')),
            ('iso', _('ISO Certified')),
        ],
        help_text=_('Type of certification held.')
    )

    # Farm contact and business information
    farm_name = models.CharField(
        _('farm name'),
        max_length=200,
        blank=True,
        help_text=_('Official name of the farm.')
    )

    business_registration = models.CharField(
        _('business registration number'),
        max_length=100,
        blank=True,
        help_text=_('Official business registration number.')
    )

    tax_id = models.CharField(
        _('tax identification number'),
        max_length=100,
        blank=True,
        help_text=_('Tax identification number.')
    )

    # Farm coordinates for location services
    latitude = models.DecimalField(
        _('latitude'),
        max_digits=10,
        decimal_places=8,
        blank=True,
        null=True,
        help_text=_('Farm latitude coordinates.')
    )

    longitude = models.DecimalField(
        _('longitude'),
        max_digits=11,
        decimal_places=8,
        blank=True,
        null=True,
        help_text=_('Farm longitude coordinates.')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'farmer_profiles'
        verbose_name = _('Farmer Profile')
        verbose_name_plural = _('Farmer Profiles')
        
    def __str__(self):
        return f"Farmer Profile: {self.farmer.full_name}"


class BuyerProfile(models.Model):
    """
    Buyer-specific profile information
    Based on the buyer_profiles table from farm2market.sql
    """
    buyer = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='buyer_profile',
        limit_choices_to={'user_type': 'buyer'}
    )
    
    location = models.CharField(
        _('location'),
        max_length=100,
        blank=True,
        help_text=_('Buyer\'s location/address.')
    )
    
    # Enhanced buyer profile fields
    company_name = models.CharField(
        _('company name'),
        max_length=200,
        blank=True,
        help_text=_('Name of the company (if applicable).')
    )

    business_type = models.CharField(
        _('business type'),
        max_length=100,
        blank=True,
        choices=[
            ('individual', _('Individual')),
            ('retailer', _('Retailer')),
            ('wholesaler', _('Wholesaler')),
            ('restaurant', _('Restaurant')),
            ('hotel', _('Hotel')),
            ('supermarket', _('Supermarket')),
            ('distributor', _('Distributor')),
            ('processor', _('Food Processor')),
            ('exporter', _('Exporter')),
            ('other', _('Other')),
        ],
        help_text=_('Type of business.')
    )

    business_registration = models.CharField(
        _('business registration number'),
        max_length=100,
        blank=True,
        help_text=_('Official business registration number.')
    )

    tax_id = models.CharField(
        _('tax identification number'),
        max_length=100,
        blank=True,
        help_text=_('Tax identification number.')
    )

    preferred_products = models.TextField(
        _('preferred products'),
        blank=True,
        help_text=_('Types of products the buyer is interested in.')
    )

    bio = models.TextField(
        _('biography'),
        blank=True,
        help_text=_('Brief description about the buyer/business.')
    )

    # Purchase preferences
    preferred_payment_method = models.CharField(
        _('preferred payment method'),
        max_length=50,
        blank=True,
        choices=[
            ('cash', _('Cash')),
            ('bank_transfer', _('Bank Transfer')),
            ('mobile_money', _('Mobile Money')),
            ('credit_card', _('Credit Card')),
            ('check', _('Check')),
        ],
        help_text=_('Preferred payment method.')
    )

    average_order_value = models.DecimalField(
        _('average order value'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Average order value in local currency.')
    )

    purchase_frequency = models.CharField(
        _('purchase frequency'),
        max_length=20,
        blank=True,
        choices=[
            ('daily', _('Daily')),
            ('weekly', _('Weekly')),
            ('monthly', _('Monthly')),
            ('seasonal', _('Seasonal')),
            ('occasional', _('Occasional')),
        ],
        help_text=_('How frequently the buyer makes purchases.')
    )

    # Verification and trust
    is_verified_buyer = models.BooleanField(
        _('is verified buyer'),
        default=False,
        help_text=_('Whether the buyer has been verified.')
    )

    verification_documents = models.FileField(
        _('verification documents'),
        upload_to='buyer_verification/',
        blank=True,
        null=True,
        help_text=_('Upload verification documents.')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'buyer_profiles'
        verbose_name = _('Buyer Profile')
        verbose_name_plural = _('Buyer Profiles')
        
    def __str__(self):
        return f"Buyer Profile: {self.buyer.full_name}"


class AdminProfile(models.Model):
    """
    Admin-specific profile information
    Based on the admin_profiles table from farm2market.sql
    """
    admin = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='admin_profile',
        limit_choices_to={'user_type': 'admin'}
    )
    
    privileges = models.TextField(
        _('privileges'),
        blank=True,
        help_text=_('Admin privileges and permissions.')
    )
    
    department = models.CharField(
        _('department'),
        max_length=100,
        blank=True,
        help_text=_('Admin department or role.')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'admin_profiles'
        verbose_name = _('Admin Profile')
        verbose_name_plural = _('Admin Profiles')
        
    def __str__(self):
        return f"Admin Profile: {self.admin.full_name}"


class EmailVerificationToken(models.Model):
    """
    Model for email verification tokens.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_verification_tokens'
    )
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Email Verification Token')
        verbose_name_plural = _('Email Verification Tokens')

    def __str__(self):
        return f"Email verification for {self.user.email}"

    @property
    def is_expired(self):
        """Check if token is expired."""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if token is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired

    def mark_as_used(self):
        """Mark token as used."""
        self.is_used = True
        self.save(update_fields=['is_used'])


class SMSVerificationToken(models.Model):
    """
    Model for SMS verification tokens.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sms_verification_tokens'
    )
    token = models.CharField(max_length=6)  # 6-digit code
    phone_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _('SMS Verification Token')
        verbose_name_plural = _('SMS Verification Tokens')

    def __str__(self):
        return f"SMS verification for {self.phone_number}"

    @property
    def is_expired(self):
        """Check if token is expired."""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if token is valid (not used, not expired, and attempts < 3)."""
        return not self.is_used and not self.is_expired and self.attempts < 3

    def increment_attempts(self):
        """Increment verification attempts."""
        self.attempts += 1
        self.save(update_fields=['attempts'])

    def mark_as_used(self):
        """Mark token as used."""
        self.is_used = True
        self.save(update_fields=['is_used'])


class PasswordResetToken(models.Model):
    """
    Model for password reset tokens.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Password Reset Token')
        verbose_name_plural = _('Password Reset Tokens')

    def __str__(self):
        return f"Password reset for {self.user.email}"

    @property
    def is_expired(self):
        """Check if token is expired."""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if token is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired

    def mark_as_used(self):
        """Mark token as used."""
        self.is_used = True
        self.save(update_fields=['is_used'])
