from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from battle.models import BattleQuestion, BattleRoom, BattleSubmission
from battle.serializers import (
    BattleQuestionSerializer, 
    BattleRoomSerializer,
    BattleRoomCreateSerializer,
    BattleSubmissionSerializer, 
    BattleResultSerializer
)

from battle.services import BattleService
from api.pagination import DefaultPagination


class BattleRoomViewSet(viewsets.ModelViewSet):
    """
    Battle room CRUD + actions.
 
    list:
        Student → only WAITING rooms (joinable) + own rooms.
        Admin   → all rooms.
        Filter: ?status=waiting|ongoing|finished|cancelled
 
    create:
        Body: { quiz, is_private }
        is_private=true → generates invite_code.
 
    join:
        Public room  → no body needed.
        Private room → body: { invite_code: "XXXXXXXX" }
 
    start:
        Only player1 can start. player2 must have joined.
 
    submit:
        Body: { question: <uuid>, answer: "a"|"b"|"c"|"d" }
        Auto-finishes when both players answer all questions.
 
    result:
        Returns score breakdown + winner.
 
    cancel:
        Only player1 can cancel a WAITING room.
 
    questions:
        Returns questions for this battle (no correct_answer leaked).
    """
    
    pagination_class   = DefaultPagination
    permission_classes = [IsAuthenticated]   
    filter_backends    = [DjangoFilterBackend, OrderingFilter]
    filterset_fields   = ["status"]
    ordering_fields    = ["created_at"]
    ordering           = ["-created_at"]
    
    def get_queryset(self):
        user = self.request.user
        qs = BattleRoom.objects.select_related(
            "player1", "player2", "winner", "quiz"
        ).prefetch_related("battle_usages")
        
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
        room = self.get_object()
        invite_code = request.data.get("invite_code")
        
        #private room - validate invite  code
        if room.invite_code:
            if not invite_code:
                return Response(
                    {"detail": "This is a private room. provide invite code."},
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
        room = self.get_object()
        serializer = BattleSubmissionSerializer(
            data = request.data,
            context={"request": request, "battle": room},
        )
        serializer.is_valid(raise_exception=True)
        question = serializer.validated_data["question"]
        answer = serializer.validated_data["answer"]
        
        try:
            submission = BattleService.submit_answer(
                room=room, user=request.user, question=question, answer=answer
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(
            {
                "is_correct": submission.is_correct,
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
 
        serializer = BattleResultSerializer(data)
        return Response(serializer.data)
    
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
 
        questions = room.battle_usages.select_related("question").order_by("order")
        serializer = BattleQuestionSerializer(questions, many=True)
        return Response(serializer.data)