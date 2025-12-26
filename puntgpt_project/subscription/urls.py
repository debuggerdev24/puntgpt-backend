from django.urls import path
from subscription.views .subscription_loading_views import *
from subscription.views.current_subscription_views import *

urlpatterns = [
   path('subscription-plan/', SubscriptionLoadingView.as_view(), name='subscription'),
   path('current-subscription/', CurrentSubscriptionView.as_view(), name='current-subscription'),
]