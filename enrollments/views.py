from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from enrollments.models import Enrollment
from enrollments import serializers as sz

from api.pagination import DefaultPagination
from api.permissions import IsAdminUser

class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    Enrollment CRUD with role-base access.
    list:
        Student → own enrollments only.
        Admin   → all enrollments.
        Filter: ?course=, ?is_completed=
        Ordering: enrolled_at, progress
    retrieve:
        Student → own only.
        Admin   → any.
    create:
        Student only. Body: { course: <uuid> }
        Validates: course must be PUBLISHED, no duplicate enrollment.
    destroy:
        Student can unenroll (own only). Admin can delete any.
    progress:
        Student updates own progress (0-100).
        Auto-marks is_completed=True when progress hits 100.
    """
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    pagination_class = DefaultPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["is_completed", "course"]
    Ordering_fields = ["enrolled_at", "progress"]
    ordering = ["-enrolled_at"]
    
    def get_queryset(self):
        user = self.request.user
        qs = Enrollment.objects.select_related(
            "student", "course", "course__instructor"
        )
        if user.is_staff:
            return qs
        #student own enrollment only
        return qs.filter(student=user)
    
    def get_serializer_class(self):
        if self.action == "create":
            return sz.EnrollmentCreateSerializer
        if self.action == "retrieve":
            return sz.EnrollmentListSerializer
        if self.action == "progress":
            return sz.EnrollmentListSerializer
        return sz.ProgressUpdateSerializer
    
    def get_permissions(self):
        if self.action == "create":
            #Only Student can enroll 
            return [IsAuthenticated()]
        return [IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        #Block teachers and admin from enrolling
        if request.user.role != "student":
            return Response(
                {"detail": "Only students can enroll in course."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        enrollment = self.get_object()
        #student can only uneroll from own enrollment 
        if not request.user.is_staff and enrollment.student != request.user:
            return Response(
                {"detail": "You can only unenroll from your own enrollments."},
                status=status.HTTP_403_FORBIDDEN,
            )
        enrollment.delete()
        return Response(
            {"message": "Successfully unenrolled."},
            status=status.HTTP_200_OK,
        )
 
    @action(detail=True, methods=["patch"], url_path="progress")
    def progress(self, request, pk=None):
        enrollment = self.get_object()

        if enrollment.student != request.user and not request.user.is_staff:
            return Response(
                {"detail": "You can only update your own progress."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProgressUpdateSerializer(
            enrollment, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            EnrollmentDetailSerializer(enrollment, context={"request": request}).data
        )