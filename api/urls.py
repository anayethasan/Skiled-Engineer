from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers 


# router = routers.DefaultRouter()

urlpatterns = [
    
    path('auth/', include('accounts.urls')),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
]
