import uuid
from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.conf import settings

class Enrollment(models.Model):
    id = models.URLField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        limit_choices_to={"role": "student"},
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    #0-100 percentage of course completion
    progress = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinLengthValidator(0), MaxLengthValidator(100)],
    )
    is_completed = models.BooleanField(default=False)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "enrollments"
        unique_together = ("student", "course")
        ordering = ["-enrolled_at"]
        
    def __str__(self):
        return f"{self.student.name}"
    
