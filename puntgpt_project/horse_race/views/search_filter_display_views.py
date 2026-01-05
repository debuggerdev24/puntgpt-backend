from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.utils.response import success_response, error_response
from subscription.models import UserSubscription


class SearchFilterDisplayView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try: 
            user = request.user
            subscription = UserSubscription.objects.filter(user=user).first()

            if not subscription:
                response, code = error_response(
                    "User does not have a subscription.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
                return Response(response, status=code)

            current_subscription = subscription.plan.plan
           
            if current_subscription == "Free ‘Mug Punter’ Account":
                allowed_filters = [
                        "jump","track", "placed_last_start", "placed_at_distance", "placed_at_track", "odds_range"]
            else:
                allowed_filters = [
                        "jump","track", "placed_last_start", "placed_at_distance", "placed_at_track", "odds_range",
                        "wins_at_track", "win_at_distance", "won_last_start", "won_last_12_months",
                        "jockey_horse_wins","jockey_strike_rate_last_12_months", "barrier"
                    ]

            response, code = success_response(
                "Search filter displaying successfully",
                data=allowed_filters,
                status_code=status.HTTP_200_OK
            )

            return Response(response, status=code)
        
        except Exception as e:
            response, code = error_response(
                "Search filter displaying failed",
                errors={"detail": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

            return Response(response, status=code)