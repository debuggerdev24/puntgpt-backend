from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.utils.response import success_response, error_response


class TipSlipView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Add the tip slip logic here
        
        pass