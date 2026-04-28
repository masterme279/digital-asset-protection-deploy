"""
Custom User Model for SENTINEL
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom manager for User model where email is the unique identifier
    for authentication instead of usernames.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model for SENTINEL platform.
    Uses email as username instead of default username field.
    """
    username = None  # Remove username field
    email = models.EmailField(unique=True, help_text="Email address (used for login)")
    full_name = models.CharField(max_length=255, help_text="Full name of the user")
    contact_no = models.CharField(max_length=20, help_text="Contact number")

    # Hook the custom manager
    objects = UserManager()

    # Set email as the USERNAME_FIELD
    USERNAME_FIELD = 'email'
    # These fields will be prompted for when running 'createsuperuser'
    REQUIRED_FIELDS = ['full_name', 'contact_no']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    @property
    def is_active_user(self):
        return self.is_active

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else ""