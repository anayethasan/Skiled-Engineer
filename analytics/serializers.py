from rest_framework import serializers
from analytics.models import MistakeAnalysis, MistakeLog, CoursesAnalytics, Purchase


class MistakeLogSerializer(serializers.ModelSerializer):
    user_name     = serializers.CharField(source="user.name", read_only=True)
    user_email    = serializers.CharField(source="user.email", read_only=True)
    question_text = serializers.CharField(source="question.question_text", read_only=True)
    course_title  = serializers.CharField(source="question.quiz.course.title", read_only=True)

    class Meta:
        model  = MistakeLog
        fields = [
            "id", "user_name", "user_email", "question_text",
            "course_title", "correct_answer", "topic", "source", "created_at",
        ]
        read_only_fields = fields


class MistakeAnalysisSerializer(serializers.ModelSerializer):
    user_name  = serializers.CharField(source="user.name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model  = MistakeAnalysis
        fields = [
            "id", "user_name", "user_email",
            "topic", "mistake_count", "suggestion", "last_update",
        ]
        read_only_fields = fields


class CoursesAnalyticsSerializer(serializers.ModelSerializer):
    course_title      = serializers.CharField(source="course.title", read_only=True)
    course_department = serializers.CharField(source="course.department.name", read_only=True)
    instructor_name   = serializers.CharField(source="course.instructor.name", read_only=True)

    class Meta:
        model  = CoursesAnalytics
        fields = [
            "id", "course", "course_title", "course_department",
            "instructor_name", "date", "total_enrollments",
            "new_enrollments", "revenue", "created_at",
        ]
        read_only_fields = fields


class CoursesAnalyticsSummarySerializer(serializers.Serializer):
    total_revenue         = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_enrollments     = serializers.IntegerField()
    total_new_enrollments = serializers.IntegerField()
    period_days           = serializers.IntegerField()
    from_date             = serializers.DateField()
    to_date               = serializers.DateField()


class PurchaseSerializer(serializers.ModelSerializer):  
    user_name    = serializers.CharField(source="user.name", read_only=True)
    user_email   = serializers.CharField(source="user.email", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model  = Purchase
        fields = [
            "id", "user", "user_name", "user_email",
            "course", "course_title", "amount", "status",
            "gateway", "gateway_transaction_id", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user_name", "user_email", "course_title",
            "gateway_transaction_id", "created_at", "updated_at",
        ]


class AdminDashboardSerializer(serializers.Serializer):
    total_revenue_7d = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_revenue_30d = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_enrollments_7d = serializers.IntegerField()
    total_enrollments_30d = serializers.IntegerField()
    popular_courses = serializers.ListField(child=serializers.DictField())
    top_students = serializers.ListField(child=serializers.DictField())
    total_courses = serializers.IntegerField()
    total_students = serializers.IntegerField()
    total_teachers = serializers.IntegerField()