from django.db import transaction
from django.utils import timezone

from quizzes.models import Quiz, Question, QuizAnswer, QuizAttempt
from analytics.models import MistakeLog

class QuizService:
    #start attempt
    @staticmethod
    @transaction.atomic
    
    def start_attempt(quiz, student) -> QuizAttempt:
        """
        Create a new IN_PROGRESS attempt.
        Blocks if student already has an IN_PROGRESS attempt for this quiz.
        """
        
        existing = QuizAttempt.objects.filter(
            student=student,
            quiz=quiz,
            status=QuizAttempt.Status.IN_PROGRESS,
        ).first()
        
        if existing:
            raise ValueError("You are already have an ongoing attempt for this quiz.")
        return QuizAttempt.objects.create(student=student, quiz=quiz)
    
    #Submit single answer
    
    @staticmethod
    @transaction.atomic()
    def submit_answer(attempt: QuizAttempt, question: Question, selected_answer: str) -> QuizAnswer:
        """
        Record one answer. Auto-finishes when all questions answered.
        Logs wrong answers to MistakeLog.
        """
        
        is_correct = selected_answer.upper() == question.correct_answer.upper()
        
        answer = QuizAnswer.objects.create(
            attempt=attempt,
            question=question,
            selected_answer=selected_answer.upper(),
            is_correct=is_correct,
        )
        
        #if answer is wrong -> analytics will MistakeLog
        if not is_correct:
            MistakeLog.objects.get_or_create(
                user=attempt.student,
                question=question,
                source="quiz",
                defaults={
                    "correct_answer": question.correct_answer,
                    "topic": question.topic,
                }
            )
            
        #auto finished if all questions answered
        total = attempt.quiz.questions.count()
        answer = attempt.answers.count()
        
        if answer >= total:
            QuizService._finish_attempt(attempt)
            
        return answer
    
    #Finish attempt (manual or auto)
    @staticmethod
    @transaction.atomic
    def finish_attempt(attempt: QuizAttempt) -> QuizAttempt:
        """Manually finish an attempt time out"""
        
        if attempt.status != QuizAttempt.Status.IN_PROGRESS:
            raise ValueError("Attempt is not in progress.")
        return QuizService._finish_attempt(attempt)
    
    @staticmethod
    def _finish_attempt(attempt: QuizAttempt) -> QuizAttempt:
        score = attempt.answer.filter(is_correct=True).count()
        attempt.score = score
        attempt.status = QuizAttempt.Status.COMPLETED
        attempt.finished_at = timezone.now()
        attempt.save(update_fields=["score", "status", "finished_at"])
        return attempt
    
    #timeout attempt
    @staticmethod
    @transaction.atomic
    def timeout_attempt(attempt: QuizAttempt) -> QuizAttempt:
        """Mark attempt as timed out score whatever is answer so far."""
        score = attempt.answers.filter(is_correct=True).count()
        attempt.score = score
        attempt.status = QuizAttempt.Status.TIMED_OUT
        attempt.finished_at = timezone.now()
        attempt.save(update_fields=["score", "status", "finished_at"])
        return attempt
    