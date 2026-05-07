from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

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
from .services import MistakeService, AnalyticsService, PurchaseService
from .filters import MistakeLogFilter, MistakeAnalysisFilter, CoursesAnalyticsFilter, PurchaseFilter
from api.pagination import DefaultPagination


class MistakeLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Student → own wrong-answer history.
    Admin   → all students' mistake logs.

    list:
        Student: returns paginated list of own mistakes.
        Admin:   returns all mistakes across all students.
        Supports filtering via MistakeLogFilter (source, topic, from_date, to_date).
        Admin extra filter: ?user_id=<uuid>
        Supports ordering by created_at, topic.

    retrieve:
        Returns detail of a single MistakeLog entry.

    analysis:
        GET /api/analytics/mistakes/analysis/
        Returns per-topic mistake count + suggestion for the logged-in student.
        Filters: ?topic=, ?min_mistakes=, ?max_mistakes=

    weak_topics:
        GET /api/analytics/mistakes/weak-topics/?limit=5
        Returns top N weakest topics for the logged-in student.
    """
    queryset = MistakeLog.objects.select_related(
        "user",
        "question",
        "question__quiz__course",
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
        """GET /api/analytics/mistakes/analysis/"""
        qs = MistakeAnalysis.objects.filter(
            user=request.user
        ).order_by("-mistake_count")

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
            return self.get_paginated_response(
                MistakeAnalysisSerializer(page, many=True).data
            )
        return Response(MistakeAnalysisSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="weak-topics")
    def weak_topics(self, request):
        """GET /api/analytics/mistakes/weak-topics/?limit=5"""
        limit  = int(request.query_params.get("limit", 5))
        topics = MistakeService.get_weakest_topics(user=request.user, limit=limit)
        data   = MistakeAnalysisSerializer(topics, many=True).data
        return Response({"count": len(data), "results": data})


class CourseAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin only. Daily course-level snapshots.

    list:
        Returns paginated list of all course analytics snapshots.
        Supports filtering via CoursesAnalyticsFilter (course, from_date, to_date).
        Supports ordering by date, total_enrollments, revenue.

    retrieve:
        Returns detail of a single snapshot entry.

    summary:
        GET /api/analytics/course-stats/summary/?days=7
        Aggregated revenue + enrollment totals for last N days.
    """
    queryset = CoursesAnalytics.objects.select_related(
        "course",
        "course__department",
        "course__instructor",
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
        """GET /api/analytics/course-stats/summary/?days=7"""
        days   = int(request.query_params.get("days", 7))
        data   = AnalyticsService.get_summary(days=days)
        serial = CoursesAnalyticsSummarySerializer(data)
        return Response(serial.data)


class PurchaseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin only. All course purchases.

    list:
        Returns paginated list of all purchases.
        Supports filtering via PurchaseFilter (status, course, from_date, to_date).
        Admin extra filter: ?user_id=<uuid>
        Supports ordering by created_at, amount, status.

    retrieve:
        Returns detail of a single purchase entry.
    """
    queryset = Purchase.objects.select_related(
        "user",
        "course",
    ).order_by("-created_at")

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
    Admin only. Single endpoint for all dashboard metrics.
    GET /api/analytics/dashboard/
    Returns revenue totals, enrollment totals, popular courses,
    top students, and platform-wide counts.
    """
    permission_classes = [IsAdminUser]

    def list(self, request):
        data   = AnalyticsService.get_dashboard()
        serial = AdminDashboardSerializer(data)
        return Response(serial.data, status=status.HTTP_200_OK)