from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from courses.models import Course, Department
from courses import serializers as sz

from api.permissions import IsTeacherOrAdmin, IsOwnerOrAdmin, IsAdminUser
from api.pagination import DefaultPagination

class DepartmentViewSet(viewsets.ModelViewSet):
    """
    Admin only CRUD for all departments
    """
    queryset = Department.objects.annotate(
        course_count=Count("courses")
    ).order_by("name")
    
    serializer_class = sz.DepartmentSerializer
    permission_classes = [IsAdminUser]
    pagination_class = DefaultPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    

class CourseViewSet(viewsets.ModelViewSet):
    """
    Course CRUD with role based access
    list:
        Student/Public → only PUBLISHED courses.
        Teacher        → own courses (all statuses).
        Admin          → all courses.
        Supports: ?status=, ?department=, ?is_free=, search, ordering.
    retrieve:
        Student → only PUBLISHED.
        Teacher → own courses only.
        Admin   → any.
    create:
        Teacher/Admin only. instructor auto-set to request.user.
    update / partial_update:
        Owner teacher or Admin only.
    destroy:
        Owner teacher or Admin only.
    publish:
        Owner teacher or Admin. Changes status DRAFT → PUBLISHED.
    archive:
        Owner teacher or Admin. Changes status → ARCHIVED.
    my_courses:
        Teacher → own courses list.
    """
    
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "is_free", "department"]
    search_fields = ["title", "description", "instructor__name"]
    ordering_fields = ["created_at", "price", "title"]
    ordering = ["-created_at"]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    
    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.select_related(
            "instructor", "department"
            ).annotate(enrolled_count=Count("enrollments"))
        
        if not user.is_authenticated:
            return qs.filter(status=Course.Status.PUBLISHED)
        
        if user.is_staff:
            return qs
        if user.role == "teacher":
            return qs.filter(instructor=user)
        return qs.filter(status=Course.Status.PUBLISHED)
    
    def get_serializer_class(self):
        if self.action == "create":
            return sz.CourseCreateSerializer
        if self.action in ["update", "partial_update"]:
            return sz.CourseUpdateSerializer
        if self.action == "retrieve":
            return sz.CourseDetailSerializer
        return sz.CourseListSerializer
    
    def get_permissions(self):
        if self.action in ["create"]:
            return [IsTeacherOrAdmin()]
        if self.action in ["update", "partial_update", "destroy", "publish", "archive"]:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [AllowAny()]
    
    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        course = self.get_object()
        
        if course.status == Course.Status.PUBLISHED:
            return Response(
                {"detail": "Course is already published"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        course.status = Course.Status.PUBLISHED 
        course.save(update_fields=["status"])
        return Response(sz.CourseDetailSerializer(course).data)
    
    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        course = self.get_object()
        if course.status == Course.Status.ARCHIVED:
            return Response(
                {"detail": "Course is already archived."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        course.status = Course.Status.ARCHIVED
        course.save(update_fields=["status"])
        return Response(sz.CourseDetailSerializer(course).data)
    
    @action(detail=False, methods=["get"], url_path="my-courses", permission_classes=[IsTeacherOrAdmin])
    def my_courses(self, request):
        """Teacher -> own courses with all statuses"""
        qs = Course.objects.filter(
            instructor=request.user
        ).select_related("department").annotate(
            enrolled_count=Count("enrollments")
        ).order_by("-created_at")
        
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                sz.CourseListSerializer(page, many=True).data
            )
        return Response(sz.CourseListSerializer(qs, many=True).data)