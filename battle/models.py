import uuid
from django.db import models
from django.conf import settings

class BattleRoom(models.Model):
    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        ONGOING = "ongoing", "Ongoing"
        FINISHED = "finished", "Finished"
        CANCELLED = "cancelled", "Cancelled"
        
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    player1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="battles_as_player1",
    )
    player2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="battles_as_player2",
    )
    quiz = models.ForeignKey(
        "quizzes.Quiz",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="battle_rooms",
    )
    
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.WAITING,
    )
    
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="battles_won",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "battle_rooms"
        ordering = ["-created_at"]
    
    def __str__(self):
        p2 = self.player2.name if self.player2 else "waiting.."
        return f"Battle: {self.player1.name} vs {p2} [{self.status}]"

class BattleQuestion(models.Model):
    """Questions assigned to specific BattleRoom (subset of quiz quest)."""
    
    ud = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)
    battle = models.ForeignKey(
        "quizzes.Question", on_delete=models.CASCADE, related_name="battle_usages",
    )
    order = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        db_table = "battle_questions"
        unique_together = ("battle", "question")
        ordering = ["order"]
    
    def __str__(self):
        return f"Battle {self.battle.id} - Q{self.order}: {self.question.question_text[:40]}"
    
class BattleSubmission(models.Model):
    """A single answer submitted by a player during a battle."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    battle = models.ForeignKey(
        BattleRoom, on_delete=models.CASCADE, related_name="submissions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="battle_submissions",
    )
    question = models.ForeignKey(
        "quizzes.Question", on_delete=models.CASCADE, related_name="battle_submissions",
    )
    answer = models.CharField(max_length=20)
    is_correct = models.BooleanField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "battle_submissions"
        unique_together = ("battle", "user", "question")
        ordering = ["submitted_at"]
        
    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} {self.user.name} in Battle {self.battle.id}"
    