from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer, UserSerializer as BaseUserSerializer
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(BaseUserCreateSerializer):
    """
    post/auth/users/ -> create new account
    """
    
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ["id", "name", "first_name", "last_name", "email", "phone_number", "address", "role", "password",]
        read_only_fields = ["id"]

class ProfileSerializer(BaseUserSerializer):
    """
    get/auth/user/me -> for see my profile
    """
    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = ["id", "name", "first_name", "last_name", "email", "phone_number", "address","role", "profile", "is_verified", "date_joined", "created_at", "update_at",]

        read_only_fields = ["id", "email", "role", "is_verified", "date_joined", "created_at", "updated_at",]

class ProfileUpdateSerializer(BaseUserSerializer):
    """PATCH/auth/users/me -> profile update"""
    
    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = ["name", "first_name", "last_name", "phone_number", "address"]
        
class AvatarSerializer(serializers.ModelSerializer):
    """
    patch/auth/me/avatar -> for update your profile picture
    delete/auth/me/avatar/ -> for profile picture remove
    """
    
    class Meta:
        model = User
        fields = ["profile"]

