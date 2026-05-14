from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from enrollments.models import Enrollment
from enrollments import serializers as sz
from api.pagination import DefaultPagination


class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    Manage course enrollments with role-based access.

    list:
        GET /enrollments/
        Returns a paginated list of enrollments.
        Student: only their own enrollments.
        Admin: all enrollments across all students.

        Filters:
            - is_completed (bool): true or false.
            - course (uuid): Filter by course ID.

        Ordering: enrolled_at, progress
        Example: GET /enrollments/?is_completed=false&ordering=-enrolled_at

    retrieve:
        GET /enrollments/<id>/
        Returns full detail of a single enrollment including course info.
        Student: own enrollments only. Admin: any.

    create:
        POST /enrollments/
        Student only. Enrolls the authenticated student in a course.
        Teachers and admins are blocked from enrolling.

        Validations:
            - Course must be PUBLISHED.
            - Student cannot enroll in the same course twice.

        Request body:
            - course (uuid, required): The course to enroll in.

        Responses:
            201: Enrolled successfully.
            400: Already enrolled or course not published.
            403: Non-student caller.

        Example:
            POST /enrollments/
            { "course": "<uuid>" }

    destroy:
        DELETE /enrollments/<id>/
        Unenroll from a course. Student can only unenroll from own enrollment.
        Admin can delete any enrollment.

        Responses:
            200: Successfully unenrolled.
            403: Attempting to unenroll another student's enrollment.

        Example:
            DELETE /enrollments/<id>/

    progress:
        PATCH /enrollments/<id>/progress/
        Update the student's progress for an enrollment (0–100).
        Student can only update own progress. Admin can update any.
        Automatically sets is_completed=True and records completed_at
        when progress reaches 100.

        Request body:
            - progress (int, required): Value between 0 and 100.

        Responses:
            200: Progress updated. Returns full enrollment detail.
            400: Progress value out of range.
            403: Attempting to update another student's progress.

        Example:
            PATCH /enrollments/<id>/progress/
            { "progress": 75 }
    """

    http_method_names  = ["get", "post", "patch", "delete", "head", "options"]
    pagination_class   = DefaultPagination
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, OrderingFilter]
    filterset_fields   = ["is_completed", "course"]
    ordering_fields    = ["enrolled_at", "progress"]   
    ordering           = ["-enrolled_at"]

    def get_queryset(self):
        user = self.request.user
        qs   = Enrollment.objects.select_related(
            "student", "course", "course__instructor"
        )
        if user.is_staff:
            return qs
        return qs.filter(student=user)

    def get_serializer_class(self):
        if self.action == "create":
            return sz.EnrollmentCreateSerializer
        if self.action == "retrieve":
            return sz.EnrollmentDetailSerializer      
        if self.action == "progress":
            return sz.ProgressUpdateSerializer        
        return sz.EnrollmentListSerializer            

    def create(self, request, *args, **kwargs):
        if request.user.role != "student":
            return Response(
                {"detail": "Only students can enroll in courses."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        enrollment = self.get_object()
        if not request.user.is_staff and enrollment.student != request.user:
            return Response(
                {"detail": "You can only unenroll from your own enrollments."},
                status=status.HTTP_403_FORBIDDEN,
            )
        enrollment.delete()
        return Response({"message": "Successfully unenrolled."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="progress")
    def progress(self, request, pk=None):
        enrollment = self.get_object()

        if enrollment.student != request.user and not request.user.is_staff:
            return Response(
                {"detail": "You can only update your own progress."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = sz.ProgressUpdateSerializer(      
            enrollment, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            sz.EnrollmentDetailSerializer(              
                enrollment, context={"request": request}
            ).data
        )