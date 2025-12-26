from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from accounts.utils.response import success_response, error_response
from subscription.models import *
import os
from django.conf import settings
import json


class SubscriptionLoadingView(APIView):
    def get(self, request):
        file_path = os.path.join(settings.BASE_DIR, 'subscription', 'utils', 'subscription.json')

        if not os.path.exists(file_path):
           response, code = error_response(
               "Subscription file not found.",
               status_code=status.HTTP_404_NOT_FOUND
           )
           return Response(response, status=code)
        
        try:
            with open(file_path, encoding='utf-8') as f:
                subscription_plans = json.load(f)
        except json.JSONDecodeError:
            response, code = error_response(
                "Invalid subscription file format.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
            return Response(response, status=code)

        saved_plans = []
        for plan in subscription_plans:
            months = plan["fields"]["duration_months"]
            obj, created = SubscriptionPlan.objects.update_or_create(
                plan=plan["fields"]["plan"],
                defaults={
                    "price": plan["fields"]["price"],
                    "features": plan["fields"]["features"]["items"],
                    "duration_months": months, 
                    "product_id_ios": plan["fields"]["product_id_ios"],
                    "product_id_android": plan["fields"]["product_id_android"]
                }
            )

            duration_label = "Free" if months == 0 else f"{months} month" if months == 1 else f"{months} months"

            saved_plans.append({
                "id": obj.id,
                "plan": obj.plan,
                "price": obj.price,
                "features": obj.features,
                "duration_label": duration_label,
                "product_id_ios": obj.product_id_ios,
                "product_id_android": obj.product_id_android
            })

        response, code = success_response(
            saved_plans,
            status_code=status.HTTP_200_OK
        )
        return Response(response, status=code)





        

           
            
