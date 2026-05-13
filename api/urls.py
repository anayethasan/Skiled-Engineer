from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers 
from analytics.views import MistakeLogViewSet, CourseAnalyticsViewSet, PurchaseViewSet, AdminDashboardViewSet
from battle.views import BattleRoomViewSet
from courses.views import CourseViewSet, DepartmentViewSet
from enrollments.views import EnrollmentViewSet
from quizzes.views import QuizViewSet, QuestionViewSet, QuizAttemptViewSet

router = routers.DefaultRouter()
router.register("mistakes", MistakeLogViewSet, basename="mistakes")
router.register("course-stats", CourseAnalyticsViewSet, basename="course-stats")
router.register("purchases", PurchaseViewSet, basename="purchases")
router.register("dashboard", AdminDashboardViewSet, basename="dashboard")
router.register("rooms", BattleRoomViewSet, basename="battle-rooms")
router.register("courses", CourseViewSet, basename="courses")
router.register("departments", DepartmentViewSet, basename="departments")
router.register("enrollments", EnrollmentViewSet, basename="enrollments")

#course Nested Routing
quiz_router = routers.NestedDefaultRouter(router, "courses", lookup="course")
quiz_router.register("quizzes", QuizViewSet, basename="course-quizzes")

question_router = routers.NestedDefaultRouter(quiz_router, "quizzes", lookup="quiz")
question_router.register("questions", QuestionViewSet, basename="quiz-questions")

attempt_router = routers.NestedDefaultRouter(quiz_router, "quizzes", lookup="quiz")
attempt_router.register("attempts", QuizAttemptViewSet, basename="quiz-attempts")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(quiz_router.urls)),
    path("", include(question_router.urls)),
    path("", include(attempt_router.urls)),
    
    path('auth/', include('accounts.urls')),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
]
