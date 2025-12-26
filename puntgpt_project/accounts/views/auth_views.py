from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from accounts.serializers.auth_serializers import *
from accounts.utils.response import success_response, error_response
from rest_framework.permissions import IsAuthenticated

class RegisterAPIView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            response, status_code = success_response(
                "User registered successfully!!",
                data={"id": user.id, "email": user.email},
                status_code=status.HTTP_201_CREATED
            )
            return Response(response, status=status_code)

        # Handle all validation errors cleanly
        response, status_code = error_response(
            "Validation error",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        return Response(response, status=status_code)
    

class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            data = serializer.validated_data

            response, code = success_response(
                "Login successful",
                data=data,
                status_code=status.HTTP_200_OK
            )
            return Response(response, status=code)

        response, code = error_response(
            "Login failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        return Response(response, status=code)
    


class ForgotPasswordView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()

            response, code = success_response(
                "Reset token sent to email.",
                data=serializer.validated_data,
                status_code=status.HTTP_200_OK
            )
            return Response(response, status=code)

        response, code = error_response(
            "Failed to send reset token.",
            errors=serializer.errors
        )
        return Response(response, status=code)
    


class VerifyResetTokenView(APIView):
    def post(self, request, user_id):
        serializer = VerifyResetTokenSerializer(
            data=request.data,
            context={"user_id": user_id}
        )

        if serializer.is_valid():
            try:
                user = User.objects.get(id=user_id)
                user.is_reset_token_verified = True
                user.save()

                response, code = success_response(
                    "Reset token is valid.",
                    status_code=status.HTTP_200_OK
                )
                return Response(response, status=code)

            except User.DoesNotExist:
                response, code = error_response(
                    "User not found.",
                    status_code=status.HTTP_404_NOT_FOUND
                )
                return Response(response, status=code)

        response, code = error_response(
            "Reset token is invalid.",
            errors=serializer.errors
        )
        return Response(response, status=code)



class ResetPasswordView(APIView):
    def post(self, request, user_id):
        serializer = ResetPasswordSerializer(
            data=request.data,
            context={'user_id': user_id}
        )

        if serializer.is_valid():
            serializer.save()

            response, code = success_response(
                "Password reset successfully.",
                status_code=status.HTTP_200_OK
            )
            return Response(response, status=code)

        response, code = error_response(
            "Password reset failed.",
            errors=serializer.errors
        )
        return Response(response, status=code)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")

        if not refresh:
            response, code = error_response(
                "Refresh token is required.",
                errors={"refresh": ["This field is required."]}
            )
            return Response(response, status=code)

        try:
            token = RefreshToken(refresh)
            token.blacklist()

            request.user.logged_out = True
            request.user.save()

            response, code = success_response(
                "Logged out successfully.",
                status_code=status.HTTP_200_OK
            )
            return Response(response, status=code)

        except Exception as e:
            response, code = error_response(
                "Invalid token.",
                errors={"detail": str(e)}
            )
            return Response(response, status=code)



