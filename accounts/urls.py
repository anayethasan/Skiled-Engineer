from django.urls import path
from accounts import views


urlpatterns = [
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("me/avatar/", views.AvatarView.as_view(), name="auth-me-avatar"),
    path("me/deactivate/", views.AccountDeactivateView.as_view(), name="auth-me-deactivate"),
]
