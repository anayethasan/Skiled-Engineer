from django.contrib.auth import get_user_model
from django.utils import timezone
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
    """this logout view where user can logout"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        refresh_token = request.data.get("refresh")
        
        if not refresh_token:
            return Response({"details": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST,)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST,)
        return Response({"message": "Logged out successfully!"}, status=status.HTTP_200_OK)
    
class AvatarView(APIView):
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
        return Response({"massage": "Avatar removed."}, status=status.HTTP_200_OK)
    
class AccountDeactivateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        user = request.user
        password = request.data.get("password")
        
        if not password or not user.check_password(password):
            return Response({"detail": "Correct password is required to deactivate your account."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save()
        
        return Response({"message": "Account deactivated successfully."}, status=status.HTTP_200_OK,)
    