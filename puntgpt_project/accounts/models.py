from django.db import models
from django.contrib.auth.models import AbstractUser
from .manager import UserManager
from django.utils import timezone
from datetime import timedelta
import random
# Create your models here.

class User(AbstractUser):
    username = None
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    state = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)

    is_18_plus = models.BooleanField(default=True)

    logged_out = models.BooleanField(default=False)

    reset_token = models.CharField(max_length=4, blank=True, null=True)
    reset_token_expiry = models.DateTimeField(blank=True, null=True)
    is_reset_token_verified = models.BooleanField(default=False)

    agreed_to_terms = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def generate_reset_token(self):
        self.reset_token = str(random.randint(1000, 9999))
        # Change expiry to 1 minute
        self.reset_token_expiry = timezone.now() + timedelta(minutes=1)
        self.save()


    def is_reset_token_valid(self, token):
        return (
            str(self.reset_token) == str(token) and
            self.reset_token_expiry and
            timezone.now() < self.reset_token_expiry
        )
    
    def verify_reset_token(self, token):
        if self.is_reset_token_valid(token):
            self.is_reset_token_verified = True
            self.save()
            return True
        return False

    def __str__(self):
        return self.email