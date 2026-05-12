from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers 
from analytics.views import MistakeLogViewSet, CourseAnalyticsViewSet, PurchaseViewSet, AdminDashboardViewSet
from battle.views import BattleRoomViewSet
from courses.views import CourseViewSet, DepartmentViewSet
from enrollments.views import EnrollmentViewSet

router = routers.DefaultRouter()
router.register("mistakes", MistakeLogViewSet, basename="mistakes")
router.register("course-stats", CourseAnalyticsViewSet, basename="course-stats")
router.register("purchases", PurchaseViewSet, basename="purchases")
router.register("dashboard", AdminDashboardViewSet, basename="dashboard")
router.register("rooms", BattleRoomViewSet, basename="battle-rooms")
router.register("courses", CourseViewSet, basename="courses")
router.register("departments", DepartmentViewSet, basename="departments")
router.register("enrollments", EnrollmentViewSet, basename="enrollments")

urlpatterns = [
    path("", include(router.urls)),
    
    path('auth/', include('accounts.urls')),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
]
