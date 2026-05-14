from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from battle.models import BattleRoom
from battle.serializers import (
    BattleQuestionSerializer,
    BattleRoomSerializer,
    BattleRoomCreateSerializer,
    BattleSubmissionSerializer,
    BattleResultSerializer,
)
from battle.services import BattleService
from api.pagination import DefaultPagination


class BattleRoomViewSet(viewsets.ModelViewSet):
    """
    Create and manage real-time quiz battle rooms between two students.

    list:
        GET /battle/rooms/
        Returns paginated battle rooms.
        Student: WAITING rooms (joinable) + own rooms (all statuses).
        Admin: all rooms.

        Filters:
            - status (string): 'waiting', 'ongoing', 'finished', 'cancelled'.

        Ordering: created_at
        Example: GET /battle/rooms/?status=waiting

    retrieve:
        GET /battle/rooms/<id>/
        Returns full detail of a single battle room.
        Student: own rooms or waiting rooms only.
        Admin: any room.

    create:
        POST /battle/rooms/
        Creates a new battle room. The authenticated user becomes player1.

        Request body:
            - quiz (uuid, required): The quiz to use for this battle.
            - is_private (bool, default=false): If true, generates an invite_code
              that must be shared with player2 to join.

        Responses:
            201: Room created. If private, invite_code is returned.
            400: Validation error.

        Example:
            POST /battle/rooms/
            { "quiz": "<uuid>", "is_private": true }

    join:
        POST /battle/rooms/<id>/join/
        Join an existing WAITING battle room as player2.
        Public room: no body required.
        Private room: must provide the correct invite_code.

        Request body (private room only):
            - invite_code (string, required): 8-character code from the room creator.

        Responses:
            200: Joined successfully. Returns updated room detail.
            400: Room full, already a player, wrong invite_code, or not waiting.

        Example (public):
            POST /battle/rooms/<id>/join/

        Example (private):
            POST /battle/rooms/<id>/join/
            { "invite_code": "AB12CD34" }

    start:
        POST /battle/rooms/<id>/start/
        Start the battle. Only player1 (room creator) can call this.
        Requires player2 to have joined. Randomly selects questions from the quiz.

        Responses:
            200: Battle started. Returns updated room with status='ongoing'.
            400: Room not in WAITING state, no player2, or no quiz assigned.
            403: Caller is not player1.

        Example:
            POST /battle/rooms/<id>/start/

    submit:
        POST /battle/rooms/<id>/submit/
        Submit a single answer during an ongoing battle.
        Auto-finishes the battle when both players have answered all questions.
        Wrong answers are automatically logged to MistakeLog.

        Request body:
            - question (uuid, required): The question being answered.
            - answer (string, required): Selected option — 'a', 'b', 'c', or 'd'.

        Responses:
            201: Answer recorded. Returns is_correct and submitted_at.
            400: Battle not ongoing, question not in battle, or already answered.

        Example:
            POST /battle/rooms/<id>/submit/
            { "question": "<uuid>", "answer": "b" }

    result:
        GET /battle/rooms/<id>/result/
        Returns the final score breakdown and winner after the battle finishes.

        Response fields:
            - winner: Player who answered more correctly (null if draw).
            - is_draw (bool): True if both players scored equally.
            - player1 / player2: correct, wrong, total, score breakdown.

        Responses:
            200: Result data.
            400: Battle is not finished yet.

        Example:
            GET /battle/rooms/<id>/result/

    cancel:
        POST /battle/rooms/<id>/cancel/
        Cancel a WAITING room. Only player1 can cancel.

        Responses:
            200: Room cancelled.
            400: Room is not in WAITING state.
            403: Caller is not player1.

        Example:
            POST /battle/rooms/<id>/cancel/

    questions:
        GET /battle/rooms/<id>/questions/
        Returns the list of questions assigned to this battle.
        Correct answers are NOT included — answers are revealed only via result/.
        Only accessible by the two players or admin.

        Responses:
            200: List of questions with options.
            400: Battle has not started yet.
            403: Caller is not a player in this battle.

        Example:
            GET /battle/rooms/<id>/questions/
    """

    pagination_class   = DefaultPagination
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, OrderingFilter]
    filterset_fields   = ["status"]
    ordering_fields    = ["created_at"]
    ordering           = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        qs   = BattleRoom.objects.select_related(
            "player1", "player2", "winner", "quiz"
        ).prefetch_related("battle_questions")

        if user.is_staff:
            return qs

        return qs.filter(
            Q(status=BattleRoom.Status.WAITING) |
            Q(player1=user) |
            Q(player2=user)
        ).distinct()

    def get_serializer_class(self):
        if self.action == "create":
            return BattleRoomCreateSerializer
        return BattleRoomSerializer

    @action(detail=True, methods=["post"], url_path="join")
    def join(self, request, pk=None):
        room        = self.get_object()
        invite_code = request.data.get("invite_code")

        if room.invite_code:
            if not invite_code:
                return Response(
                    {"detail": "This is a private room. Provide invite_code."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if invite_code != room.invite_code:
                return Response(
                    {"detail": "Invalid invite code."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            room = BattleService.join_room(room=room, user=request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(BattleRoomSerializer(room).data)

    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        room = self.get_object()
        try:
            room = BattleService.start_battle(room=room, user=request.user)
        except (ValueError, PermissionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BattleRoomSerializer(room).data)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        room       = self.get_object()
        serializer = BattleSubmissionSerializer(
            data=request.data,
            context={"request": request, "battle": room},
        )
        serializer.is_valid(raise_exception=True)

        try:
            submission = BattleService.submit_answer(
                room=room,
                user=request.user,
                question=serializer.validated_data["question"],
                answer=serializer.validated_data["answer"],
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "is_correct":   submission.is_correct,
                "submitted_at": submission.submitted_at,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="result")
    def result(self, request, pk=None):
        room = self.get_object()
        try:
            data = BattleService.get_result(room)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BattleResultSerializer(data).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        room = self.get_object()
        try:
            room = BattleService.cancel_room(room=room, user=request.user)
        except (ValueError, PermissionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Battle room cancelled."})

    @action(detail=True, methods=["get"], url_path="questions")
    def questions(self, request, pk=None):
        room = self.get_object()

        if room.status == BattleRoom.Status.WAITING:
            return Response(
                {"detail": "Battle has not started yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user not in [room.player1, room.player2] and not request.user.is_staff:
            return Response(
                {"detail": "You are not a player in this battle."},
                status=status.HTTP_403_FORBIDDEN,
            )

        questions  = room.battle_usages.select_related("question").order_by("order")
        serializer = BattleQuestionSerializer(questions, many=True)
        return Response(serializer.data)