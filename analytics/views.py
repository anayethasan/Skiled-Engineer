from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import MistakeLog, MistakeAnalysis, CoursesAnalytics, Purchase
from .serializers import (
    MistakeLogSerializer,
    MistakeAnalysisSerializer,
    CoursesAnalyticsSerializer,
    CoursesAnalyticsSummarySerializer,
    PurchaseSerializer,
    AdminDashboardSerializer,
)
from .services import MistakeService, AnalyticsService
from .filters import MistakeLogFilter, CoursesAnalyticsFilter, PurchaseFilter
from api.pagination import DefaultPagination


class MistakeLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View and analyze a student's wrong-answer history.
    Admins can view all students' mistake logs.

    list:
        Returns a paginated list of mistake logs.
        Student: only their own mistakes.
        Admin: all students' mistakes.

        Filters:
            - source (string): Filter by source — 'quiz' or 'battle'.
            - topic (string): Filter by topic (case-insensitive).
            - from_date (date): Only mistakes from this date onward.
            - to_date (date): Only mistakes up to this date.
            - user_id (uuid, admin only): Filter by a specific student.

        Ordering: created_at, topic
        Example: GET /analytics/mistakes/?source=quiz&topic=algebra

    retrieve:
        Returns the full detail of a single MistakeLog entry.
        Student: own entries only. Admin: any entry.

        Example: GET /analytics/mistakes/<id>/

    analysis:
        GET /analytics/mistakes/analysis/
        Returns per-topic mistake count and a suggestion string
        for the currently logged-in student.

        Filters:
            - topic (string): Filter by topic.
            - min_mistakes (int): Minimum mistake count.
            - max_mistakes (int): Maximum mistake count.

        Example: GET /analytics/mistakes/analysis/?topic=algebra&min_mistakes=3

    weak_topics:
        GET /analytics/mistakes/weak-topics/?limit=5
        Returns the top N topics with the most mistakes for the logged-in student.

        Query params:
            - limit (int, default=5): Number of topics to return.

        Example: GET /analytics/mistakes/weak-topics/?limit=10
    """

    queryset = MistakeLog.objects.select_related(
        "user", "question", "question__quiz__course",
    ).order_by("-created_at")

    serializer_class = MistakeLogSerializer
    pagination_class = DefaultPagination
    filter_backends  = [DjangoFilterBackend, OrderingFilter]
    filterset_class  = MistakeLogFilter
    ordering_fields  = ["created_at", "topic"]
    ordering         = ["-created_at"]

    def get_permissions(self):
        if self.request.user.is_staff:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_staff:
            user_id = self.request.query_params.get("user_id")
            if user_id:
                qs = qs.filter(user_id=user_id)
            return qs
        return qs.filter(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="analysis")
    def analysis(self, request):
        qs    = MistakeAnalysis.objects.filter(user=request.user).order_by("-mistake_count")
        topic = request.query_params.get("topic")
        min_m = request.query_params.get("min_mistakes")
        max_m = request.query_params.get("max_mistakes")
        if topic:
            qs = qs.filter(topic__icontains=topic)
        if min_m:
            qs = qs.filter(mistake_count__gte=min_m)
        if max_m:
            qs = qs.filter(mistake_count__lte=max_m)

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(MistakeAnalysisSerializer(page, many=True).data)
        return Response(MistakeAnalysisSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="weak-topics")
    def weak_topics(self, request):
        limit  = int(request.query_params.get("limit", 5))
        topics = MistakeService.get_weakest_topics(user=request.user, limit=limit)
        data   = MistakeAnalysisSerializer(topics, many=True).data
        return Response({"count": len(data), "results": data})


class CourseAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin only. Daily snapshot analytics for each course.

    list:
        Returns a paginated list of course analytics snapshots.
        Each record represents one day's data for one course.

        Filters:
            - course (uuid): Filter by course ID.
            - from_date (date): Snapshots from this date onward.
            - to_date (date): Snapshots up to this date.

        Ordering: date, total_enrollments, revenue
        Example: GET /analytics/course-stats/?from_date=2025-01-01

    retrieve:
        Returns the full detail of a single analytics snapshot.

        Example: GET /analytics/course-stats/<id>/

    summary:
        GET /analytics/course-stats/summary/?days=7
        Returns aggregated totals for revenue, enrollments, and new
        enrollments over the last N days.

        Query params:
            - days (int, default=7): Number of past days to aggregate.
              Use days=30 for a monthly summary.

        Example: GET /analytics/course-stats/summary/?days=30
    """

    queryset = CoursesAnalytics.objects.select_related(
        "course", "course__department", "course__instructor",
    ).order_by("-date")

    serializer_class   = CoursesAnalyticsSerializer
    permission_classes = [IsAdminUser]
    pagination_class   = DefaultPagination
    filter_backends    = [DjangoFilterBackend, OrderingFilter]
    filterset_class    = CoursesAnalyticsFilter
    ordering_fields    = ["date", "total_enrollments", "revenue"]
    ordering           = ["-date"]

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        days   = int(request.query_params.get("days", 7))
        data   = AnalyticsService.get_summary(days=days)
        serial = CoursesAnalyticsSummarySerializer(data)
        return Response(serial.data)


class PurchaseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin only. View all course purchase records.

    list:
        Returns a paginated list of all purchases across all students.

        Filters:
            - status (string): Filter by purchase status — 'pending', 'completed', 'failed'.
            - course (uuid): Filter by course ID.
            - from_date (date): Purchases from this date onward.
            - to_date (date): Purchases up to this date.
            - user_id (uuid): Filter by a specific student.

        Ordering: created_at, amount, status
        Example: GET /analytics/purchases/?status=completed&course=<uuid>

    retrieve:
        Returns the full detail of a single purchase record.

        Example: GET /analytics/purchases/<id>/
    """

    queryset = Purchase.objects.select_related("user", "course").order_by("-created_at")

    serializer_class   = PurchaseSerializer
    permission_classes = [IsAdminUser]
    pagination_class   = DefaultPagination
    filter_backends    = [DjangoFilterBackend, OrderingFilter]
    filterset_class    = PurchaseFilter
    ordering_fields    = ["created_at", "amount", "status"]
    ordering           = ["-created_at"]

    def get_queryset(self):
        qs      = super().get_queryset()
        user_id = self.request.query_params.get("user_id")
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs


class AdminDashboardViewSet(viewsets.ViewSet):
    """
    Admin only. Single endpoint returning all key platform metrics.

    list:
        GET /analytics/dashboard/
        Returns a comprehensive dashboard snapshot including:
            - total_revenue_7d: Total revenue from the last 7 days.
            - total_revenue_30d: Total revenue from the last 30 days.
            - total_enrollments_7d: New enrollments in the last 7 days.
            - total_enrollments_30d: New enrollments in the last 30 days.
            - popular_courses: Top 5 most enrolled courses (last 30 days).
            - top_students: Top 5 students by completed courses.
            - total_courses: Total number of courses on the platform.
            - total_students: Total number of student accounts.
            - total_teachers: Total number of teacher accounts.

        Example: GET /analytics/dashboard/
    """

    permission_classes = [IsAdminUser]

    def list(self, request):
        data   = AnalyticsService.get_dashboard()
        serial = AdminDashboardSerializer(data)
        return Response(serial.data, status=status.HTTP_200_OK)