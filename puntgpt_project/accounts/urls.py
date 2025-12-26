from django.urls import path
from accounts.views.auth_views import *
from accounts.views.profile_views import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView)


urlpatterns = [

    # auth urls
    path('register/', RegisterAPIView.as_view(), name='register'),

    path("login/", LoginAPIView.as_view(), name="login"),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('verify-reset-token/<int:user_id>/', VerifyResetTokenView.as_view(), name='verify-reset-token'),
    path('reset-password/<int:user_id>/', ResetPasswordView.as_view(), name='reset-password'),

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),

    # profile urls
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile-update'),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),

]