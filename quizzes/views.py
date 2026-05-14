from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from quizzes.models import Quiz, Question, QuizAttempt
from quizzes import serializers as sz
from quizzes.services import QuizService
from api.pagination import DefaultPagination
from api.permissions import IsTeacherOrAdmin


class QuizViewSet(viewsets.ModelViewSet):
    """
    Manage quizzes nested under a course.
    Base URL: /courses/<course_pk>/quizzes/

    list:
        GET /courses/<course_pk>/quizzes/
        Returns all quizzes for the given course.
        All authenticated users can list quizzes.

        Search: title, description.
        Ordering: created_at, title.
        Example: GET /courses/<course_pk>/quizzes/?ordering=title

    retrieve:
        GET /courses/<course_pk>/quizzes/<id>/
        Returns full detail of a quiz including question_count and attempt_count.

    create:
        POST /courses/<course_pk>/quizzes/
        Teacher (own course) or Admin only.

        Request body:
            - title (string, required)
            - description (string, optional)
            - time_limit_minutes (int, optional): Time limit in minutes. Null = no limit.

        Responses:
            201: Quiz created.
            403: Caller is not the course instructor or admin.

        Example:
            POST /courses/<course_pk>/quizzes/
            { "title": "Chapter 1 Quiz", "time_limit_minutes": 30 }

    update / partial_update:
        PUT/PATCH /courses/<course_pk>/quizzes/<id>/
        Teacher (own course) or Admin only.

    destroy:
        DELETE /courses/<course_pk>/quizzes/<id>/
        Teacher (own course) or Admin only.
        Deletes all associated questions and attempts.
    """

    pagination_class = DefaultPagination
    filter_backends  = [SearchFilter, OrderingFilter]
    search_fields    = ["title", "description"]
    ordering_fields  = ["created_at", "title"]
    ordering         = ["created_at"]

    def get_queryset(self):
        return Quiz.objects.filter(
            course_id=self.kwargs.get("course_pk")
        ).annotate(
            question_count=Count("questions", distinct=True),
            attempt_count=Count("attempts", distinct=True),   
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
        course = Course.objects.get(pk=self.kwargs.get("course_pk"))
        if not self.request.user.is_staff and course.instructor != self.request.user:
            raise PermissionDenied("You can only add quizzes to your own courses.")
        serializer.save(course=course)


class QuestionViewSet(viewsets.ModelViewSet):
    """
    Manage questions nested under a quiz.
    Base URL: /courses/<course_pk>/quizzes/<quiz_pk>/questions/

    list:
        GET /courses/<course_pk>/quizzes/<quiz_pk>/questions/
        Returns all questions for the given quiz.
        Student: questions WITHOUT correct_answer field.
        Teacher / Admin: questions WITH correct_answer field.

        Filters:
            - difficulty (string): 'easy', 'medium', 'hard'.
            - topic (string): Exact match on topic.

        Ordering: created_at, difficulty.
        Example: GET .../questions/?difficulty=hard&ordering=created_at

    retrieve:
        GET .../questions/<id>/
        Same access rules as list — correct_answer shown only to teacher/admin.

    create:
        POST .../questions/
        Teacher (own course) or Admin only.
        Options must include keys A, B, C, D.
        correct_answer must be one of A, B, C, D.

        Request body:
            - question_text (string, required)
            - options (JSON, required): e.g. {"A": "...", "B": "...", "C": "...", "D": "..."}
            - correct_answer (string, required): 'A', 'B', 'C', or 'D'.
            - topic (string, required): Used for MistakeLog tracking.
            - difficulty (string, default='medium'): 'easy', 'medium', or 'hard'.

        Example:
            POST .../questions/
            {
                "question_text": "What is 2+2?",
                "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
                "correct_answer": "B",
                "topic": "arithmetic",
                "difficulty": "easy"
            }

    update / partial_update:
        PUT/PATCH .../questions/<id>/
        Teacher (own course) or Admin only.

    destroy:
        DELETE .../questions/<id>/
        Teacher (own course) or Admin only.
    """

    pagination_class = DefaultPagination
    filter_backends  = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["difficulty", "topic"]         
    ordering_fields  = ["created_at", "difficulty"]
    ordering         = ["created_at"]

    def get_queryset(self):
        return Question.objects.filter(
            quiz_id=self.kwargs.get("quiz_pk"),
            quiz__course_id=self.kwargs.get("course_pk"),
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
            pk=self.kwargs.get("quiz_pk"),
            course_id=self.kwargs.get("course_pk"),
        )
        if not self.request.user.is_staff and quiz.course.instructor != self.request.user:
            raise PermissionDenied("You can only add questions to your own quizzes.")
        serializer.save(quiz=quiz)


class QuizAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Track and manage student quiz attempts.
    Base URL: /courses/<course_pk>/quizzes/<quiz_pk>/attempts/

    list:
        GET .../attempts/
        Returns paginated attempts for the given quiz.
        Student: only own attempts.
        Teacher / Admin: all attempts for this quiz.

        Filters:
            - status (string): 'in_progress', 'completed', 'timed_out'.

        Ordering: started_at, score.
        Example: GET .../attempts/?status=completed&ordering=-score

    retrieve:
        GET .../attempts/<id>/
        Returns full attempt detail including all submitted answers.
        Student: own attempt only. Teacher/Admin: any.

    start:
        POST .../attempts/start/
        Student only. Must be enrolled in the course.
        Creates a new IN_PROGRESS attempt.
        Blocked if student already has an ongoing attempt for this quiz.

        Responses:
            201: Attempt created. Returns attempt detail with empty answers list.
            403: Caller is not a student or not enrolled in the course.
            400: Already has an ongoing attempt.

        Example:
            POST .../attempts/start/

    submit:
        POST .../attempts/<id>/submit/
        Submit a single answer for the attempt.
        The attempt must be IN_PROGRESS and belong to the caller.
        Each question can only be answered once.
        Wrong answers are automatically logged to MistakeLog (source='quiz').
        Auto-finishes the attempt (status=completed) when all questions are answered.

        Request body:
            - question (uuid, required): The question being answered.
            - selected_answer (string, required): 'A', 'B', 'C', or 'D'.

        Responses:
            201: Answer recorded. Returns is_correct, answered_at, attempt_status, score.
            400: Question not in quiz, already answered, or attempt not in progress.
            403: Attempt belongs to another student.

        Example:
            POST .../attempts/<id>/submit/
            { "question": "<uuid>", "selected_answer": "B" }

    finish:
        POST .../attempts/<id>/finish/
        Manually finish an IN_PROGRESS attempt (early submit or time-out).
        Score is calculated from answers submitted so far.
        Student can only finish own attempt. Admin can finish any.

        Responses:
            200: Attempt finished. Returns full attempt detail with final score.
            400: Attempt is not in progress.
            403: Attempt belongs to another student.

        Example:
            POST .../attempts/<id>/finish/
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
            quiz_id=self.kwargs.get("quiz_pk"),
            quiz__course_id=self.kwargs.get("course_pk"),
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
        attempt = self.get_object()

        if attempt.student != request.user:
            return Response(
                {"detail": "You can only submit to your own attempt."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = sz.SubmitAnswerSerializer(         
            data=request.data,
            context={"attempt": attempt},
        )
        serializer.is_valid(raise_exception=True)

        answer = QuizService.submit_answer(
            attempt=attempt,
            question=serializer.validated_data["question"],
            selected_answer=serializer.validated_data["selected_answer"],
        )

        attempt.refresh_from_db()
        return Response(
            {
                "is_correct":     answer.is_correct,
                "answered_at":    answer.answered_at,
                "attempt_status": attempt.status,
                "score":          attempt.score,
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

        return Response(sz.AttemptDetailSerializer(attempt).data)    