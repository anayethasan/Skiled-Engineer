from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from quizzes.models import Quiz, Question, QuizAttempt
from quizzes import serializers as sz

from quizzes.services import QuizService
from api.pagination import DefaultPagination
from api.permissions import IsTeacherOrAdmin, IsOwnerOrAdmin
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

class QuizViewSet(viewsets.ModelViewSet):
    """
    Nested under courses:
    list:
        Student (enrolled) → quiz list, no correct_answer.
        Teacher (own course) / Admin → full list.
    create:
        Teacher (own course) / Admin only.
    update/partial_update:
        Teacher (own course) / Admin only.
    destroy:
        Teacher (own course) / Admin only.
    """
    
    pagination_class = DefaultPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "title"]
    ordering = ["created_at"]
    
    def get_queryset(self):
        return Quiz.objects.filter(
            course_id=self.kwargs["course_pk"]
        ).annotate(
            question_count = Count("questions", distinct=True),
            attempt_count = Count("attempts", distinct=True),
        ).select_related("course")
        
    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return sz.QuizWriteSerializer
        
        if self.action == "retrieve":
            return sz.QuizDetailSerializer
        
        return sz.QuizListSerializer
    
    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsTeacherOrAdmin()]
        return [IsAuthenticated()]
 
    def perform_create(self, serializer):
        from courses.models import Course
        course = Course.objects.get(pk=self.kwargs["course_pk"])
 
        if not self.request.user.is_staff and course.instructor != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only add quizzes to your own courses.")
 
        serializer.save(course=course)
        
class QuestionViewSet(viewsets.ModelViewSet):
    """
    Nested under quizzes
    Student → questions without correct_answer.
    Teacher/Admin → questions with correct_answer.
    """

    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["difficulty", "topic"]
    ordering_fields = ["created_at", "difficulty"]
    ordering = ["created_at"]
    
    def get_queryset(self):
        return Question.objects.filter(
            quiz_id=self.kwargs["quiz_pk"],
            quiz__course_id=self.kwargs["course_pk"],
        )
        
    def get_serializer_class(self):
        user = self.request.user
        if self.action in ["create", "update", "partial_update"]:
            return sz.QuestionWriteSerializer
        
        if user.is_staff or getattr(user, "role", None) == "teacher":
            return sz.QuestionDetailSerializer
        
        return sz.QuestionListSerializer
    
    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsTeacherOrAdmin()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        quiz = Quiz.objects.select_related("course").get(
            pk=self.kwargs["quiz_pk"],
            course_id=self.kwargs["course_pk"],
        )
        if not self.request.user.is_staff and quiz.course.instructor != self.request.user:
            raise PermissionDenied("You can only add question to your quizzes.")
        serializer.save(quiz=quiz)
        
class QuizAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:
        Teacher/Admin → all attempts for this quiz.
 
    retrieve:
        Own attempt (student) / any (teacher+admin).
 
    start:
        Student only. Creates IN_PROGRESS attempt.
 
    submit:
        Auto-finishes when all questions answered.
 
    finish:
        Manually finish (early submit or timeout).
    """
    
    pagination_class   = DefaultPagination
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, OrderingFilter]
    filterset_fields   = ["status"]
    ordering_fields    = ["started_at", "score"]
    ordering           = ["-started_at"]
 
    def get_queryset(self):
        user = self.request.user
        qs   = QuizAttempt.objects.filter(
            quiz_id=self.kwargs["quiz_pk"],
            quiz__course_id=self.kwargs["course_pk"],
        ).select_related("student", "quiz").prefetch_related("answers")
 
        if user.is_staff or getattr(user, "role", None) == "teacher":
            return qs
        return qs.filter(student=user)
 
    def get_serializer_class(self):
        if self.action == "retrieve":
            return sz.AttemptDetailSerializer
        return sz.AttemptSerializer
    
    
    @action(detail=False, methods=["post"], url_path="start")
    def start(self, request, course_pk=None, quiz_pk=None):
        if request.user.role != "student":
            return Response(
                {"detail": "Only students can attempt quizzes."},
                status=status.HTTP_403_FORBIDDEN,
            )
 
        # Must be enrolled
        from enrollments.models import Enrollment
        if not Enrollment.objects.filter(
            student=request.user, course_id=course_pk
        ).exists():
            return Response(
                {"detail": "You must be enrolled in this course to attempt the quiz."},
                status=status.HTTP_403_FORBIDDEN,
            )
 
        try:
            quiz    = Quiz.objects.get(pk=quiz_pk, course_id=course_pk)
            attempt = QuizService.start_attempt(quiz=quiz, student=request.user)
        except Quiz.DoesNotExist:
            return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
 
        return Response(sz.AttemptDetailSerializer(attempt).data, status=status.HTTP_201_CREATED)
    
    
    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, course_pk=None, quiz_pk=None, pk=None):
        attempt    = self.get_object()
 
        if attempt.student != request.user:
            return Response(
                {"detail": "You can only submit to your own attempt."},
                status=status.HTTP_403_FORBIDDEN,
            )
 
        serializer = SubmitAnswerSerializer(
            data=request.data,
            context={"attempt": attempt},
        )
        serializer.is_valid(raise_exception=True)
 
        answer = QuizService.submit_answer(
            attempt=attempt,
            question=serializer.validated_data["question"],
            selected_answer=serializer.validated_data["selected_answer"],
        )
 
        # Refresh attempt to get updated status
        attempt.refresh_from_db()
        return Response(
            {
                "is_correct":  answer.is_correct,
                "answered_at": answer.answered_at,
                "attempt_status": attempt.status,
                "score": attempt.score,
            },
            status=status.HTTP_201_CREATED,
        )
        
    @action(detail=True, methods=["post"], url_path="finish")
    def finish(self, request, course_pk=None, quiz_pk=None, pk=None):
        attempt = self.get_object()
 
        if attempt.student != request.user and not request.user.is_staff:
            return Response(
                {"detail": "You can only finish your own attempt."},
                status=status.HTTP_403_FORBIDDEN,
            )
 
        try:
            attempt = QuizService.finish_attempt(attempt)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
 
        return Response(AttemptDetailSerializer(attempt).data)