from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from accounts.serializers.profile_serializers import *
from rest_framework.permissions import IsAuthenticated
from accounts.utils.response import success_response, error_response


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            serializer = ProfileSerializer(request.user)

            response, code = success_response(
                "Profile fetched successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
            return Response(response, status=code)

        except Exception as e:
            response, code = error_response(
                "Failed to fetch profile.",
                errors={"detail": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            return Response(response, status=code)
        


class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        try:
            serializer = ProfileSerializer(request.user,data=request.data,partial=True)

            if not serializer.is_valid():
                response, code = error_response(
                    message="Validation failed",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
                return Response(response, status=code)

            serializer.save()

            response, code = success_response(
                message="Profile updated successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
            return Response(response, status=code)

        except Exception as e:
            response, code = error_response(
                message="Failed to update profile",
                errors={"detail": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            return Response(response, status=code)
        


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            response, code = success_response(
                message="Password changed successfully",
                data=None,
                status_code=status.HTTP_200_OK
            )
            return Response(response, status=code)

        response, code = error_response(
            message="Password change failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        return Response(response, status=code)



       
