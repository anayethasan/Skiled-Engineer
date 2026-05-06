from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from accounts.models import User, EmailVerificationToken


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    list_display  = ("email", "name", "role", "is_verified", "is_active", "is_staff", "date_joined")
    list_filter   = ("role", "is_staff", "is_active", "is_verified")
    search_fields = ("email", "name", "first_name", "last_name", "phone_number")
    ordering      = ("email",)

    fieldsets = (
        (None, {
            "fields": ("email", "password")
        }),
        ("Personal Info", {
            "fields": ("name", "first_name", "last_name", "phone_number", "address")
        }),
        ("Role & Verification", {
            "fields": ("role", "is_verified")
        }),
        ("Permissions", {
            "fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")
        }),
        ("Important Dates", {
            "fields": ("last_login", "date_joined")
        }),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email", "name",
                "password1", "password2",
                "role", "is_verified",
                "is_staff", "is_active",
            ),
        }),
    )
    readonly_fields = ("date_joined", "last_login")


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display  = ("user", "token", "created_at", "expires_at")
    search_fields = ("user__email",)
    readonly_fields = ("token", "created_at")