from django.contrib import admin
from quizzes.models import Question, Quiz, QuizAnswer, QuizAttempt

admin.site.register(Question)
admin.site.register(Quiz)
admin.site.register(QuizAnswer)
admin.site.register(QuizAttempt)
