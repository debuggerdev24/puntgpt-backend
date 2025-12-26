from django.db import models
from accounts.models import User

# Create your models here.
class SubscriptionPlan(models.Model):
    plan = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    features = models.JSONField()
    duration_months = models.IntegerField()
    product_id_ios = models.CharField(max_length=255, blank=True, null=True)
    product_id_android = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.plan
    
class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, )
    plan = models.ForeignKey("SubscriptionPlan", on_delete=models.CASCADE)