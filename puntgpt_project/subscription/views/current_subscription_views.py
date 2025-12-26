from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from accounts.utils.response import success_response, error_response
from subscription.models import UserSubscription
from rest_framework.permissions import IsAuthenticated
from django.forms.models import model_to_dict


class CurrentSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            user_subscription = UserSubscription.objects.get(user=request.user)
            response, code = success_response(
                "Current subscription fetched successfully",
                data={
                    "id": user_subscription.id,
                    "user": user_subscription.user.email,
                    "plan": user_subscription.plan.plan
                },
                status_code=status.HTTP_200_OK
            )
            return Response(response, status=code)

        except UserSubscription.DoesNotExist:
            response, code = error_response(
                "User has no subscription",
                status_code=status.HTTP_404_NOT_FOUND
            )
            return Response(response, status=code)