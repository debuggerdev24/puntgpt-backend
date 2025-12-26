from django.db.models.signals import post_save
from django.dispatch import receiver
from subscription.models import UserSubscription, SubscriptionPlan
from accounts.models import User    


@receiver(post_save, sender=User)
def create_user_subscription(sender, instance, created, **kwargs):
    if created:
        try:
            free_plan = SubscriptionPlan.objects.get(plan="Free ‘Mug Punter’ Account")
            UserSubscription.objects.create(user=instance, plan=free_plan)
        except SubscriptionPlan.DoesNotExist:
            print("Free plan not found.")
        except Exception as e:
            print(f"Error creating user subscription: {str(e)}")