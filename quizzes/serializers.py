from django.utils import timezone
from rest_framework import serializers

from quizzes.models import Question, Quiz, QuizAnswer, QuizAttempt

class QuizListSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(read_only=True)
    attempt_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "time_limit_minutes", "question_count", "attempt_count", "created_at", "updated_at"]
        read_only_fields = fields
    
class QuizDetailSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    attempt_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Quiz
        fields = ["id", "course", "course_title", "title", "description", "time_limit_minutes", "question_count", "attempt_count", "created_at", "updated_at"]
        read_only_fields = fields
    

class QuizWriteSerializer(serializers.ModelSerializer):
    """Teacher cerate or update a quiz."""
    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "time_limit_minutes"]
        read_only_fields = ["id"]
        
class QuestionListSerializer(serializers.ModelSerializer):
    """"No correct_answer - used for student attempt view."""
    class Meta:
        model = Question
        fields = ["id", "question_text", "options", "topic", "difficulty", "created_at"]
        read_only_fields = fields 
        
class QuestionDetailSerializer(serializers.ModelSerializer):
    """Include correct answer for teacher and admin"""
    
    class Meta:
        model = Question
        fields = ["id", "question_text", "options", "correct_answer",
            "topic", "difficulty", "created_at",]
        read_only_fields = fields
        

class QuestionWriteSerializer(serializers.ModelSerializer):
    """Teacher create or update question"""
    
    class Meta:
        model = Question
        fields = ["id", "question_text", "options", "correct_answer", "topic", "difficulty"]
        read_only_fields = ["id"]
        
    def validate_options(self, value):
        required_keys = {"A", "B", "C", "D"}
        
        if not required_keys.issubset(value.keys()):
            raise serializers.ValidationError(
                "Options must be contain keys: A, B, C, D"
            )
        return value
    
    def validate_correct_answer(self, value):
        
        if value.upper() not in ["A", "B", "C", "D"]:
            raise serializers.ValidationError(
                "Correct Answer Must be on of: A, B, C, D."
            )
        return value.upper()
    

class QuizAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question.question_text", read_only=True)
    correct_answer = serializers.CharField(source="question.correct_answer", read_only=True)
    topic = serializers.CharField(source="question.topic", read_only=True)
    
    class Meta:
        model = QuizAnswer
        fields = [
            "id", "question", "question_text",
            "selected_answer", "correct_answer",
            "is_correct", "topic", "answered_at",
        ]
        read_only_fields = fields 
        
class AttemptSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name", read_only=True)
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    
    class Meta:
        model = QuizAttempt
        fields = ["id", "student_name", "quiz_title", "status", "score", "started_at", "finished_at"]
        read_only_fields = fields
    
    
class AttemptDetailSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name", read_only=True)
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    answers = QuizAnswerSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizAttempt
        fields = ["id", "student_name", "quiz_title", "status", "score", "total_questions", "started_at", "finished_at", "answers"]
        read_only_fields = fields
    
    def get_total_questions(self, obj):
        return obj.quiz.questions.count()
    
class SubmitAnswerSerializer(serializers.Serializer):
    """Body: { question: <uuid>, selected_answer: "A" | "B" | "C" | "D"}"""
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    selected_answer = serializers.ChoiceField(choices=["A", "B", "C", "D"])
    
    def validate(self, attrs):
        attempt = self.context["attempt"]
        question = attrs["question"]
        
        if attempt.status != QuizAttempt.Status.IN_PROGRESS:
            raise serializers.ValidationError("This attempt is not in progress.")
        
        if not attempt.quiz.questions.filter(id=question.id).exists():
            raise serializers.ValidationError("This question does not belong to this quiz.")
        if attempt.answers.filter(question=question).exists():
            raise serializers.ValidationError("You have already answered this questions.")
        
        return attrs