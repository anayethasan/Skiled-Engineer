from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers import AvatarSerializer, ProfileSerializer

User = get_user_model()


class LogoutView(APIView):
    """
    Logout the currently authenticated user.

    post:
        Blacklists the provided refresh token, effectively logging the user out.
        The access token will remain valid until it expires naturally.

        Request body:
            - refresh (string, required): The JWT refresh token to blacklist.

        Responses:
            200: Logged out successfully.
            400: Refresh token missing or invalid/expired.
            401: Not authenticated.

        Example request:
            POST /auth/logout/
            { "refresh": "<your_refresh_token>" }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"message": "Logged out successfully!"}, status=status.HTTP_200_OK)


class AvatarView(APIView):
    """
    Manage the authenticated user's profile picture.

    patch:
        Upload or replace the current user's avatar.
        Accepts multipart/form-data with a single image file.

        Request body (multipart/form-data):
            - profile (image file, required): The new avatar image.

        Responses:
            200: Updated profile data including new avatar URL.
            400: Invalid file or validation error.
            401: Not authenticated.

        Example request:
            PATCH /auth/me/avatar/
            Content-Type: multipart/form-data
            Body: profile=<image_file>

    delete:
        Remove the current user's avatar.
        Sets profile to null and deletes the file from storage.

        Responses:
            200: Avatar removed successfully.
            401: Not authenticated.

        Example request:
            DELETE /auth/me/avatar/
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request):
        serializer = AvatarSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProfileSerializer(request.user).data)

    def delete(self, request):
        user = request.user
        if user.profile:
            user.profile.delete(save=False)
            user.profile = None
            user.save()
        return Response({"message": "Avatar removed."}, status=status.HTTP_200_OK)


class AccountDeactivateView(APIView):
    """
    Deactivate (soft-delete) the authenticated user's account.

    delete:
        Sets is_active=False on the user account. The user will no longer
        be able to log in. This is a soft delete — data is preserved.
        Password confirmation is required as a safety measure.

        Request body:
            - password (string, required): The user's current password for confirmation.

        Responses:
            200: Account deactivated successfully.
            400: Password missing or incorrect.
            401: Not authenticated.

        Example request:
            DELETE /auth/me/deactivate/
            { "password": "your_current_password" }
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        password = request.data.get("password")

        if not password or not user.check_password(password):
            return Response(
                {"detail": "Correct password is required to deactivate your account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = False
        user.save()
        return Response(
            {"message": "Account deactivated successfully."},
            status=status.HTTP_200_OK,
        )