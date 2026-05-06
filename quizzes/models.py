import uuid
from django.db import models
from django.conf import settings

class Quiz(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uu, editable=False)
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="quizzes",
    )
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "quizzes"
        verbose_name_plural = "Quizzes"
        ordering = ["created_at"]
    
    def __str__(self):
        return f"{self.title} - {self.course.title}"
    
class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    # options stored as JSON: {"A": "...", "B": "...", "C": "...", "D": "..."}
    options = models.JSONField()
     # correct_answer stores the key, e.g. "A"
    correct_answer = models.CharField(max_length=10)
    
    # topic is crucial for the Mistake Tracker
    topic = models.CharField(max_length=150)
    difficulty = models.CharField(
        max_length=10,
        choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")],
        default="medium",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "questions"
    
    def __str__(self):
        return f"Q: {self.question_text[:60]}... [topic: {self.topic}]"
    
class QuizAttempt(models.Model):
    """Tracks a student's full attempt at a quiz."""
    
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        TIMED_OUT = "timed_out", "Timed Out"
        
    id = models.URLField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.IN_PROGRESS
    )
    score = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "quiz_attempts"
        ordering = ["-started_at"]
    
    def __str__(self):
        return f"{self.student.name} - {self.quiz.title} ({self.status})"

class QuizAnswer(models.Model):
    """Single answer submitted by a student within a quizAttempt."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.CASCADE, related_name="answers",
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="student_answers",
    )    
    selected_answer = models.CharField(max_length=10)
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "quiz_answers"
        unique_together = ("attempt", "question")
        
    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} {self.attempt.student.name} -> Q:{self.question.id}"