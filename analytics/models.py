import uuid
from django.db import models
from django.conf import settings


class MistakeLog(models.Model):
    """Raw record of every wrong answer a student submits."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mistake_logs",
    )
    
    question = models.ForeignKey(
        "quizzes.Question",
        on_delete=models.CASCADE,
        related_name="mistake_logs",
    )
    
    selected_answer = models.CharField(max_length=20)
    correct_answer = models.CharField(max_length=15)
    
    topic = models.CharField(max_length=150)
    
    source = models.CharField(
        max_length=10,
        choices=[("quiz", "Quiz"), ("battle", "Battle")],
        default="quiz",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "mistake_logs"
        ordering = ["-created_at"]
        
    def __str__(self):
        return f"{self.user.name} wrong on topic '{self.topic}' at {self.created_at:%Y-%m-%d}"
    
class MistakeAnalysis(models.Model):
    """
    Aggregated mistake count per (user, topic).
    Updated every time a new MistakeLog is created (via signal or service layer).
    Used to generate personalised suggestions.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mistake_analyses",
    )
    topic = models.CharField(max_length=150)
    mistake_count = models.PositiveIntegerField(default=0)
    suggestion = models.TextField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "mistake_analyses"
        unique_together = ("user", "topic")
        ordering = ["-mistake_count"]
        
    def __str__(self):
        return f"{self.user.name} — '{self.topic}': {self.mistake_count} mistakes"
    

#Admin / sales Analytics

class CoursesAnalytics(models.Model):
    """
    Daily snapshot of course-level metrics.
    Populated by a scheduled management command / Celery task.
    Kept separate from the Purchase model (future payment scope) so
    the admin dashboard remains functional even before payments land.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="analytics_snapshots",
    )
    date = models.DateField()
    total_enrollments = models.PositiveIntegerField(default=0)
    new_enrollments = models.PositiveIntegerField(default=0)
    
    # Revenue fields are zero until payment gateway is active
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "course_analytics"
        unique_together = ("course", "date")
        ordering = ["-date"]
        
    def __str__(self):
        return f"{self.course.title} — {self.date} ({self.new_enrollments} new)"
    
class Purchase(models.Model):
    """
    Stub model ready for payment gateway integration.
    Not wired to any active payment provider yet.
    """
    
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="purchases",
    )
    
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="purchases",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    # Gateway-specific fields (populate when integrating a provider)
    gateway = models.CharField(max_length=50, blank=True)
    gateway_transaction_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    gateway_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "purchases"
        ordering = ["-created_at"]
        
    def __str__(self):
        return f"{self.user.name} → {self.course.title} [{self.status}] ${self.amount}"