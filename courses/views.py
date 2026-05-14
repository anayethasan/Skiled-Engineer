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
    Admin only. Manage academic departments / course categories.

    list:
        GET /departments/
        Returns all departments with their course count.

        Search: ?search=<name>
        Ordering: name, created_at
        Example: GET /departments/?search=science&ordering=name

    retrieve:
        GET /departments/<id>/
        Returns detail of a single department.

    create:
        POST /departments/
        Admin only. Creates a new department.

        Request body:
            - name (string, required): Department name. Must be unique.
            - slug (string, required): URL-safe identifier. Must be unique.

        Example:
            POST /departments/
            { "name": "Computer Science", "slug": "computer-science" }

    update / partial_update:
        PUT/PATCH /departments/<id>/
        Admin only. Update department name or slug.

    destroy:
        DELETE /departments/<id>/
        Admin only. Deletes the department. Courses with this department
        will have department set to null (SET_NULL).
    """

    queryset = Department.objects.annotate(course_count=Count("courses")).order_by("name")

    serializer_class   = sz.DepartmentSerializer
    permission_classes = [IsAdminUser]
    pagination_class   = DefaultPagination
    filter_backends    = [SearchFilter, OrderingFilter]
    search_fields      = ["name"]
    ordering_fields    = ["name", "created_at"]
    ordering           = ["name"]


class CourseViewSet(viewsets.ModelViewSet):
    """
    Manage courses with role-based access control.

    list:
        GET /courses/
        Returns a paginated list of courses based on the caller's role.
        Student / unauthenticated: only PUBLISHED courses.
        Teacher: only their own courses (all statuses).
        Admin: all courses regardless of status.

        Filters:
            - status (string): 'draft', 'published', 'archived'.
            - department (uuid): Filter by department.
            - is_free (bool): true or false.

        Search: title, description, instructor name.
        Ordering: created_at, price, title.
        Example: GET /courses/?status=published&is_free=true&ordering=-created_at

    retrieve:
        GET /courses/<id>/
        Returns full course detail. Access rules same as list.

    create:
        POST /courses/
        Teacher or Admin only. The instructor field is automatically set
        to the authenticated user.

        Request body (multipart/form-data or JSON):
            - title (string, required)
            - description (string, required)
            - department (uuid, optional)
            - thumbnail (image, optional): Max 10 MB.
            - price (decimal, default=0.00)
            - is_free (bool, default=true)

        Example:
            POST /courses/
            { "title": "Django REST API", "description": "...", "is_free": true }

    update / partial_update:
        PUT/PATCH /courses/<id>/
        Owner teacher or Admin only. Can update all fields including status.

    destroy:
        DELETE /courses/<id>/
        Owner teacher or Admin only.

    publish:
        POST /courses/<id>/publish/
        Change course status from DRAFT → PUBLISHED.
        Owner teacher or Admin only.

        Responses:
            200: Course published. Returns updated course detail.
            400: Course is already published.

    archive:
        POST /courses/<id>/archive/
        Change course status to ARCHIVED. Archived courses are not visible
        to students.
        Owner teacher or Admin only.

        Responses:
            200: Course archived. Returns updated course detail.
            400: Course is already archived.

    my_courses:
        GET /courses/my-courses/
        Teacher only. Returns all of the authenticated teacher's courses
        across all statuses (draft, published, archived).

        Ordering: -created_at
        Example: GET /courses/my-courses/
    """

    pagination_class = DefaultPagination
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "is_free", "department"]
    search_fields    = ["title", "description", "instructor__name"]
    ordering_fields  = ["created_at", "price", "title"]
    ordering         = ["-created_at"]
    parser_classes   = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        user = self.request.user
        qs   = Course.objects.select_related(
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
        if self.action == "create":
            return [IsTeacherOrAdmin()]
        if self.action in ["update", "partial_update", "destroy", "publish", "archive"]:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [AllowAny()]

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        course = self.get_object()
        if course.status == Course.Status.PUBLISHED:
            return Response(
                {"detail": "Course is already published."},
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

    @action(
        detail=False, methods=["get"],
        url_path="my-courses",
        permission_classes=[IsTeacherOrAdmin],
    )
    def my_courses(self, request):
        qs = Course.objects.filter(
            instructor=request.user
        ).select_related("department").annotate(
            enrolled_count=Count("enrollments")
        ).order_by("-created_at")

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(sz.CourseListSerializer(page, many=True).data)
        return Response(sz.CourseListSerializer(qs, many=True).data)