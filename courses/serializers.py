from rest_framework import serializers
from courses.models import Course, Department
from api.validators import validate_file_size

class DepartmentSerializer(serializers.ModelSerializer):
    course_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Department
        fields = ["id", "name", "slug", "created_at", "course_count"]
        read_only_fields = ["id", "created_at"]

class CourseListSerializer(serializers.ModelSerializer):
    """to see all list of course any one can view this"""
    instructor_name = serializers.CharField(source="instructor.name", read_only = True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    enrolled_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Course
        fields = ["id", "title", "department_name", "instructor_name", "enrolled_count", "status", "thumbnail", "price", "is_free", "created_at"]
        read_only_fields = fields
        
class CourseDetailSerializer(serializers.ModelSerializer):
    """full details for retriveing"""
    instructor_name = serializers.CharField(source="instructor.name", read_only = True)
    instructor_email = serializers.EmailField(source="instructor.email", read_only = True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    enrolled_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Course
        fields = ["id", "title", "description", "department", "department_name", "instructor", "instructor_name", "instructor_email", "status", "thumbnail", "price", "is_free", "enrolled_count", "created_at", "updated_at",]
        read_only_fields = ["id", "instructor", "created_at", "updated_at"]
        
class CourseCreateSerializer(serializers.ModelSerializer):
    """this is for POST teacher create a course"""
    thumbnail = serializers.ImageField(required=False, validators=[validate_file_size])
    
    class Meta:
        model = Course
        fields = ["id", "title", "description", "department", "thumbnail", "price", "is_free"]
        read_only_fields = ["id"]
        
    def create(self, validated_data):
        #instructor is always the logged in as teacher
        request = self.context["request"]
        return Course.objects.create(instructor=request.user, **validated_data)

class CourseUpdateSerializer(serializers.ModelSerializer):
    """Üsed for PATCH/PUT teacher updates own courses."""
    
    thumbnail = serializers.ImageField(required=False, validators=[validate_file_size])
    
    class Meta:
        model = Course
        fields = ["title", "description", "department", "status", "thumbnail", "price", "is_free"]