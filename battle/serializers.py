import uuid
from django.contrib.auth import get_user_model
from rest_framework import serializers

from battle.models import BattleRoom, BattleQuestion, BattleSubmission

User = get_user_model()

class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "profile"]
        
class BattleQuestionSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question.question_text", read_only=True)
    option_a = serializers.CharField(source="question.option_a", read_only=True)
    option_b = serializers.CharField(source="question.option_b", read_only=True)
    option_c = serializers.CharField(source="question.option_c", read_only=True)
    option_d = serializers.CharField(source="question.option_d", read_only=True)
    
    topic = serializers.CharField(source="question.topic", read_only=True)
    
    class Meta:
        model = BattleQuestion
        fields = ["id", "order", "question_text", "option_a", "option_b", "option_c", "option_d", "topic"]

class BattleRoomSerializer(serializers.ModelSerializer):
    """Used for list/retrieve."""
    player1 = PlayerSerializer(read_only=True)
    player2 = PlayerSerializer(read_only=True)
    winner = PlayerSerializer(read_only=True)
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    total_questions = serializers.SerializerMethodField()
    
    class Meta:
        model = BattleRoom
        fields = ["id", "status", "invite_code", "player1", "player2", "winner", "quiz", "quiz_title", "total_questions", "created_at", "started_at", "finished_at",]
        read_only_fields = fields
    
    def get_total_questions(self, obj):
        return obj.battle_usages.count()
    
class BattleRoomCreateSerializer(serializers.ModelSerializer):
    """Used for post/battle/rooms/ student can create a room."""
    is_private = serializers.BooleanField(default=False, write_only=True)
    
    class Meta:
        model = BattleRoom
        fields = ["quiz", "is_private"]
    
    def create(self, validated_data):
        is_private = validated_data.pop("is_private", False)
        request = self.context["request"]
        invite_code = uuid.uuid4().hex[:8].upper() if is_private else None
        return BattleRoom.objects.create(
            player1=request.user,
            invite_code=invite_code,
            **validated_data,
        )
    
class BattleSubmissionSerializer(serializers.ModelSerializer):
    """Üsed for post/battle/rooms/{id}/submit/"""
    class Meta:
        model = BattleSubmission
        fields = ["question", "answer"]
    
    def validate(self, attrs):
        battle = self.context["battle"]
        user = self.context["request"].user
        question = attrs["question"]
        
        if battle.status != BattleRoom.Status.ONGOING:
            raise serializers.ValidationError("battle is not ongoing.")
        
        if user not in [battle.player1, battle.player2]:
            raise serializers.ValidationError("You are not a player in this battle.")
        
        if not battle.battle_usages.filter(question=question).exists():
            raise serializers.ValidationError("This question does not belong to this battle.")
        
        if BattleSubmission.objects.filter(battle=battle, user=user, question=question).exists():
            raise serializers.ValidationError("You have already answered this question.")
        
        return attrs
    
class PlayerResultSerializer(serializers.Serializer):
    """Score breakdown per player in result view."""
    player = PlayerSerializer()
    correct = serializers.IntegerField()
    wrong = serializers.IntegerField()
    total = serializers.IntegerField()
    score = serializers.IntegerField()
    
class BattleResultSerializer(serializers.Serializer):
    """used for get/battle/rooms/{id}/result/"""
    battle_id = serializers.UUIDField()
    status = serializers.CharField()
    winner = PlayerSerializer(allow_null=True)
    is_draw = serializers.BooleanField()
    player1 = PlayerResultSerializer()
    player2 = PlayerResultSerializer(allow_null=True)
    finished_at = serializers.DateTimeField()