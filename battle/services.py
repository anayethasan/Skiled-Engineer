import random
from django.db import transaction
from django.utils import timezone

from battle.models import BattleQuestion, BattleRoom, BattleSubmission
from analytics.models import MistakeLog

BATTLE_QUESTION_COUNT = 10

class BattleService:
    
    @staticmethod
    @transaction.atomic
    def join_room(room: BattleRoom, user) -> BattleRoom:
        """
        Add user as player2.
        Validates: not full, not already a player, room is WAITING.
        """
        if room.status != BattleRoom.Status.WAITING:
            raise ValueError("This battle room is no longer open.")
 
        if room.player2 is not None:
            raise ValueError("This battle room is already full.")
 
        if room.player1 == user:
            raise ValueError("You cannot join your own battle room.")
 
        room.player2 = user
        room.save(update_fields=["player2"])
        return room
    
    @staticmethod
    @transaction.atomic
    def start_battle(room: BattleRoom, user) -> BattleRoom:
        """
        Player1 starts the battle after player2 joins.
        Randomly picks BATTLE_QUESTION_COUNT questions from the quiz
        and creates BattleQuestion entries.
        """
        if room.player1 != user:
            raise PermissionError("Only the room creator can start the battle.")
 
        if room.status != BattleRoom.Status.WAITING:
            raise ValueError("Battle cannot be started in its current state.")
 
        if room.player2 is None:
            raise ValueError("Cannot start battle without a second player.")
 
        if room.quiz is None:
            raise ValueError("No quiz assigned to this battle room.")
 
        # Pick random questions from the quiz
        all_questions = list(room.quiz.questions.all())
        if len(all_questions) < BATTLE_QUESTION_COUNT:
            selected = all_questions
        else:
            selected = random.sample(all_questions, BATTLE_QUESTION_COUNT)
 
        BattleQuestion.objects.bulk_create([
            BattleQuestion(battle=room, question=q, order=i)
            for i, q in enumerate(selected)
        ])
 
        room.status     = BattleRoom.Status.ONGOING
        room.started_at = timezone.now()
        room.save(update_fields=["status", "started_at"])
        return room
    
    @staticmethod
    @transaction.atomic
    def submit_answer(room: BattleRoom, user, question, answer: str) -> BattleSubmission:
        """
        Record a player's answer. Auto-finishes battle when both players
        have answered all questions. Creates MistakeLog on wrong answer.
        """
        is_correct = (answer == question.correct_answer)
 
        submission = BattleSubmission.objects.create(
            battle=room,
            user=user,
            question=question,
            answer=answer,
            is_correct=is_correct,
        )
 
        # Log wrong answers to analytics MistakeLog
        if not is_correct:
            MistakeLog.objects.get_or_create(
                user=user,
                question=question,
                source="battle",
                defaults={
                    "correct_answer": question.correct_answer,
                    "topic": getattr(question, "topic", ""),
                },
            )
 
        # Check if both players have finished all questions
        BattleService._try_finish(room)
        return submission
    
    @staticmethod
    def _try_finish(room: BattleRoom):
        """Finish the battle if both players have answered all questions."""
        total_questions = room.battle_usages.count()
        if total_questions == 0:
            return
 
        p1_count = BattleSubmission.objects.filter(battle=room, user=room.player1).count()
        p2_count = BattleSubmission.objects.filter(battle=room, user=room.player2).count()
 
        if p1_count >= total_questions and p2_count >= total_questions:
            BattleService._finish_battle(room)
 
    @staticmethod
    @transaction.atomic
    def _finish_battle(room: BattleRoom):
        p1_score = BattleSubmission.objects.filter(
            battle=room, user=room.player1, is_correct=True
        ).count()
        p2_score = BattleSubmission.objects.filter(
            battle=room, user=room.player2, is_correct=True
        ).count()
 
        if p1_score > p2_score:
            room.winner = room.player1
        elif p2_score > p1_score:
            room.winner = room.player2
        else:
            room.winner = None 
 
        room.status      = BattleRoom.Status.FINISHED
        room.finished_at = timezone.now()
        room.save(update_fields=["status", "winner", "finished_at"])
        
    @staticmethod
    def get_result(room: BattleRoom) -> dict:
        """Build result dict for BattleResultSerializer."""
        if room.status != BattleRoom.Status.FINISHED:
            raise ValueError("Battle is not finished yet.")
 
        total = room.battle_usages.count()
 
        def player_stats(player):
            if player is None:
                return None
            correct = BattleSubmission.objects.filter(
                battle=room, user=player, is_correct=True
            ).count()
            wrong = BattleSubmission.objects.filter(
                battle=room, user=player, is_correct=False
            ).count()
            return {
                "player": player,
                "correct": correct,
                "wrong": wrong,
                "total": total,
                "score": correct,
            }
 
        return {
            "battle_id": room.id,
            "status": room.status,
            "winner": room.winner,
            "is_draw": room.winner is None,
            "player1": player_stats(room.player1),
            "player2":  player_stats(room.player2),
            "finished_at": room.finished_at,
        }
        
    @staticmethod
    @transaction.atomic
    def cancel_room(room: BattleRoom, user):
        """Player1 can cancel a WAITING room."""
        if room.player1 != user:
            raise PermissionError("Only the room creator can cancel the battle.")
        if room.status != BattleRoom.Status.WAITING:
            raise ValueError("Only waiting rooms can be cancelled.")
        room.status = BattleRoom.Status.CANCELLED
        room.save(update_fields=["status"])
        return room