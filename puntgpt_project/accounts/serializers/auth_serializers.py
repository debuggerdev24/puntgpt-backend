from rest_framework import serializers
from accounts.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
import re
from django.conf import settings
from django.core.mail import send_mail


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    # confirm_password = serializers.CharField(write_only=True)
    agreed_to_terms = serializers.BooleanField(required=True)


    class Meta:
        model = User
        fields = ('email','first_name','last_name','date_of_birth','state','phone','password',
                #'confirm_password',
                'agreed_to_terms',)
        

    def validate_agreed_to_terms(self, value):
        if not value:
            raise serializers.ValidationError("You must agree to the Terms and Conditions to register.")
        return value

    def validate(self, attrs):

        # 1. Password match check
        # if attrs.get("password") != attrs.get("confirm_password"):
        #     raise serializers.ValidationError(
        #         {"password": "Password fields do not match."}
        #     )

        # 2. Django's built-in password validators
        validate_password(attrs.get("password"))
    
        return attrs
    
    

    def create(self, validated_data):
        # validated_data.pop("confirm_password")
        password = validated_data.pop("password")
        # Always use create_user to hash password
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user
    


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError(
                {"error": "Invalid email or password"}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"error": "Your account is inactive"}
            )

        # Generate JWT
        refresh = RefreshToken.for_user(user)
        user.logged_out = False
        user.save()
        return {
            "user_id": user.id,
            "email": user.email,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
    


# class ForgotPasswordSerializer(serializers.Serializer):
#     email = serializers.EmailField()

#     def validate_email(self, value):
#         if not User.objects.filter(email=value).exists():
#             raise serializers.ValidationError("User with this email does not exist.")
#         return value

#     def save(self):
#         email = self.validated_data['email']
#         user = User.objects.get(email=email)
#         user.generate_reset_token()
#         user.save()

#         self.validated_data['user_id'] = user.id

#         send_mail(
#             subject="Your OTP Code",
#             message=f"Your OTP is: {user.reset_token}",
#             from_email=settings.DEFAULT_FROM_EMAIL, 
#             recipient_list=[user.email],
#             fail_silently=False,
#         )
#         return user

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value

    def save(self):
        email = self.validated_data['email']
        user = User.objects.get(email=email)
        # user.generate_reset_token()
        user.reset_token = "1234"
        user.save()

        self.validated_data['user_id'] = user.id

        # send_mail(
        #     subject="Your OTP Code",
        #     message=f"Your OTP is: {user.reset_token}",
        #     from_email=settings.DEFAULT_FROM_EMAIL, 
        #     recipient_list=[user.email],
        #     fail_silently=False,
        # )
        return user

# class VerifyResetTokenSerializer(serializers.Serializer):
#     reset_token = serializers.CharField()

#     def validate_reset_token(self, value):
#         user_id = self.context['user_id']
#         try:
#             user = User.objects.get(id=user_id)
#         except User.DoesNotExist:
#             raise serializers.ValidationError("Invalid user.")

#         if not user.is_reset_token_valid(value):
#             raise serializers.ValidationError("Invalid or expired token.")

#         return value

class VerifyResetTokenSerializer(serializers.Serializer):
    reset_token = serializers.CharField()

    def validate_reset_token(self, value):
        user_id = self.context['user_id']
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid user.")

        # if not user.is_reset_token_valid(value):
        #     raise serializers.ValidationError("Invalid or expired token.")
        if user.reset_token != '1234':
            raise serializers.ValidationError("Invalid or expired token.")

        return value


    

class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        pattern = re.compile(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
        )
        if not pattern.match(value):
            raise serializers.ValidationError(
                "Password must be at least 8 characters long and include at least one uppercase letter, "
                "one lowercase letter, one digit, and one special character."
            )
        return value

    def validate(self, data):
        user_id = self.context['user_id']
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid user.")

        if not user.is_reset_token_verified:
            raise serializers.ValidationError("Reset token is not verified.")

        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")

        return data

    def save(self):
        user_id = self.context['user_id']
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

        user.set_password(self.validated_data['new_password'])
        user.reset_token = None
        user.reset_token_expiry = None
        user.is_reset_token_verified = False
        user.save()
        return user

