"""
Serializers for User Authentication
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        validators=[validate_password],
        help_text="Password (min 6 characters)"
    )
    password_confirm = serializers.CharField(write_only=True, help_text="Confirm password")
    
    class Meta:
        model = User
        fields = ['full_name', 'email', 'password', 'password_confirm', 'contact_no']
        extra_kwargs = {
            'email': {'required': True},
            'full_name': {'required': True},
            'contact_no': {'required': True},
        }
    
    def validate_email(self, value):
        """Validate email uniqueness"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def create(self, validated_data):
        """Create new user with hashed password"""
        validated_data.pop('password_confirm')  # Remove confirm password
        
        # Call the custom create_user method from UserManager
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            **{k: v for k, v in validated_data.items() if k not in ['email', 'password']}
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField(help_text="Email address")
    password = serializers.CharField(write_only=True, help_text="Password")
    
    def validate(self, attrs):
        """Validate credentials and return user"""
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'),
                              username=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid credentials.')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password.')


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'contact_no', 'is_active', 'date_joined']
        read_only_fields = ['id', 'email', 'is_active', 'date_joined']
