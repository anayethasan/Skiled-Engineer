"""
analytics/signals.py
 
Fires whenever a QuizAnswer or BattleSubmission is saved with is_correct=False.
Creates a MistakeLog and increments MistakeAnalysis, then regenerates the suggestion.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from quizzes.models import QuizAnswer
from battle.models import BattleSubmission
from analytics.models import MistakeLog, MistakeAnalysis


SUGGESTION_RULES = [
    (10, "You struggle significantly with '{topic}'. Consider reviewing found amentals."),
    (5, "You often make mistake in '{topic}'. Focus on edge cases."),
    (2, "You have repeated errors in '{topic}. Review this topic carefully.'"),
]

def _handle_mistake(user, question, selected_answer, source="quiz"):
    MistakeLog.objects.create(
        user=user,
        question=question,
        selected_answer=selected_answer,
        correct_answer=question.correct_answer,
        topic=question.topic,
        source=source,
    )
    
    #Aggregated count
    from django.db.models import F
    obj, created = MistakeAnalysis.objects.get_or_create(
        user=user,
        topic=question.topic,
        defaults={"mistake_count": 1},
    )
    if not created:
        MistakeAnalysis.objects.filter(pk=obj.pk).update(mistake_count=F("mistake_count") + 1)
        obj.refresh_from_db()
        
    #Regenerate suggestion
    suggestion = ""
    for threshold, template in SUGGESTION_RULES:
        if obj.mistake_count >= threshold:
            suggestion = template.format(topic=question.topic)
            break
    if suggestion != obj.suggestion:
        MistakeAnalysis.objects.filter(pk=obj.pk).update(suggestion=suggestion)
        
@receiver(post_save, sender=QuizAnswer)
def on_quiz_answer_saved(sender, instance, created, **kwargs):
    if created and not instance.is_correct:
        _handle_mistake(
            user=instance.attempt.student,
            question=instance.question,
            selected_answer=instance.selected_answer,
            source="quiz",
        )
        
        
@receiver(post_save, sender=BattleSubmission)
def on_battle_submission_saved(sender, instance, created, **kwargs):
    if created and not instance.is_correct:
        _handle_mistake(
            user=instance.user,
            question=instance.question,
            selected_answer=instance.answer,
            source="battle",
        )