from rest_framework import serializers
from django.utils import timezone
from enrollments.models import Enrollment
from courses.models import Course

class EnrollmentListSerializer(serializers.ModelSerializer):
    """this is for list view"""
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_thumbnail = serializers.ImageField(source="course.thumbnail", read_only=True)
    instructor_name = serializers.CharField(source="course.instructor.name", read_only=True)
    
    class Meta:
        model = Enrollment
        fields = ["id", "course", "course_title", "course_thumbnail", "instructor_name", "progress", "is_completed", "enrolled_at", "completed_at"]
        read_only_fields = fields

class EnrollmentDetailSerializer(serializers.ModelSerializer):
    """Full detail used for retrieve"""
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_thumbnail = serializers.ImageField(source="course.thumbnail", read_only=True)
    instructor_name = serializers.CharField(source="course.instructor.name", read_only=True)
    student_name = serializers.CharField(source="student.name", read_only=True)
    student_email = serializers.CharField(source="student.email", read_only=True)
    
    class Meta:
        model = Enrollment
        fields = [
            "id", "student", "student_name", "student_email", "course", "course_title", 
            "course_thumbnail", "instructor_name", "progress", "is_completed", "enrolled_at", "completed_at"
        ]
        read_only_fields = fields
        
class EnrollmentCreateSerializer(serializers.ModelSerializer):
    """student enrolls in a course"""
    class Meta:
        model = Enrollment
        fields = ["course"]
        
    def validate_course(self, course):
        if course.status != Course.Status.PUBLISHED:
            raise serializers.ValidationError("You can only enroll in published courses.")
        return course
    
    def validate(self, attrs):
        request = self.context["request"]
        course = attrs["course"]
        
        if Enrollment.objects.filter(student=request.user, course=course).exists():
            raise serializers.ValidationError({"detail": "You are already enrolled in this course."})
        return attrs
    
    def create(self, validated_data):
        return Enrollment.objects.create(
            student=self.context["request"].user,
            **validated_data,
        )
    
class ProgressUpdateSerializer(serializers.ModelSerializer):
    """student update progress."""
    
    class Meta:
        model = Enrollment
        fields = ["progress"]
    
    def validate_progress(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Progress must be between 0 and 100.")
        return value
    
    def update(self, instance, validated_data):
        instance.progress = validated_data["progress"]
        
        #auto complete when progress hits 100
        if instance.progress == 100 and not instance.is_completed:
            instance.is_completed = True
            instance.completed_at = timezone.now()
        
        instance.save(update_fields=["progress", "is_completed", "completed_at"])
        return instance
    