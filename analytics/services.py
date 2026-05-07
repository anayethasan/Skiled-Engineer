"""all heavy logic here"""

from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

from analytics.models import MistakeLog, MistakeAnalysis, CoursesAnalytics, Purchase
from enrollments.models import Enrollment
from django.contrib.auth import get_user_model
from courses.models import Course


class MistakeService:

    @staticmethod
    def get_user_mistakes(user, source=None, topic=None):
        """Return MistakeLogs for a student. Optionally filter by source and/or topic."""
        qs = MistakeLog.objects.filter(user=user).select_related(
            "question", "question__quiz__course"
        )
        if source:
            qs = qs.filter(source=source)
        if topic:
            qs = qs.filter(topic__icontains=topic)
        return qs

    @staticmethod
    def get_user_analysis(user, topic=None):
        """Return MistakeAnalysis rows for a student, ordered by mistake_count desc."""
        qs = MistakeAnalysis.objects.filter(user=user)
        if topic:
            qs = qs.filter(topic__icontains=topic)
        return qs

    @staticmethod
    def get_weakest_topics(user, limit=5):   
        """Return top N weakest topics for a student."""
        return (
            MistakeAnalysis.objects
            .filter(user=user)
            .order_by("-mistake_count")[:limit]
        )

    @staticmethod
    def get_all_mistakes_admin(source=None, topic=None, user_id=None):
        """Admin: get all mistake logs with optional filters."""
        qs = MistakeLog.objects.select_related(
            "user", "question", "question__quiz__course"
        )
        if source:
            qs = qs.filter(source=source)
        if topic:
            qs = qs.filter(topic__icontains=topic)
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs


class AnalyticsService:

    @staticmethod
    def _date_range(days: int):
        today = timezone.now().date()
        return today - timedelta(days=days), today

    @staticmethod
    def get_course_snapshots(course_id=None, from_date=None, to_date=None):
        qs = CoursesAnalytics.objects.select_related(
            "course", "course__department", "course__instructor"
        )
        if course_id:
            qs = qs.filter(course_id=course_id)
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)
        return qs

    @staticmethod
    def get_summary(days: int = 7):
        from_date, to_date = AnalyticsService._date_range(days)
        agg = CoursesAnalytics.objects.filter(
            date__range=(from_date, to_date)
        ).aggregate(
            total_revenue=Sum("revenue"),
            total_enrollments=Sum("total_enrollments"),
            total_new_enrollments=Sum("new_enrollments"),
        )
        return {
            "total_revenue":         agg["total_revenue"]         or Decimal("0.00"),
            "total_enrollments":     agg["total_enrollments"]     or 0,
            "total_new_enrollments": agg["total_new_enrollments"] or 0,
            "period_days":           days,
            "from_date":             from_date,
            "to_date":               to_date,
        }

    @staticmethod  
    def get_popular_courses(days: int = 30, limit: int = 5):
        from_date, _ = AnalyticsService._date_range(days)
        return (
            Enrollment.objects
            .filter(enrolled_at__date__gte=from_date)
            .values("course_id", "course__title", "course__instructor__name")
            .annotate(enrollment_count=Count("id"))
            .order_by("-enrollment_count")[:limit]
        )

    @staticmethod
    def get_top_students(limit: int = 5):
        return (
            Enrollment.objects
            .filter(is_completed=True)
            .values("student__id", "student__name", "student__email")
            .annotate(completed_courses=Count("id"))
            .order_by("-completed_courses")[:limit]
        )

    @staticmethod
    def get_dashboard():
        User = get_user_model()
        s7  = AnalyticsService.get_summary(7)
        s30 = AnalyticsService.get_summary(30)
        return {
            "total_revenue_7d":      s7["total_revenue"],
            "total_revenue_30d":     s30["total_revenue"],
            "total_enrollments_7d":  s7["total_enrollments"],
            "total_enrollments_30d": s30["total_enrollments"],
            "popular_courses": list(
                AnalyticsService.get_popular_courses(days=30, limit=5)
            ),
            "top_students": list(
                AnalyticsService.get_top_students(limit=5)
            ),
            "total_courses":  Course.objects.count(),
            "total_students": User.objects.filter(role="student").count(),
            "total_teachers": User.objects.filter(role="teacher").count(),
        }


class PurchaseService:

    @staticmethod
    def get_all_purchase(status=None, user_id=None, course_id=None):
        qs = Purchase.objects.select_related("user", "course")
        if status:
            qs = qs.filter(status=status)
        if user_id:
            qs = qs.filter(user_id=user_id)
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs

    @staticmethod
    def get_user_purchases(user):
        return Purchase.objects.filter(user=user).select_related("course")

    @staticmethod
    @transaction.atomic
    def create_purchase(user, course, amount, gateway=""):
        """your payment provider here. Returns a Purchase in PENDING state."""
        existing = Purchase.objects.filter(
            user=user, course=course, status=Purchase.Status.PENDING
        ).first()
        if existing:
            return existing
        return Purchase.objects.create(
            user=user, course=course, amount=amount,
            status=Purchase.Status.PENDING, gateway=gateway,
        )

    @staticmethod
    @transaction.atomic
    def confirm_purchase(purchase, gateway_transaction_id, gateway_response=None):
        """Mark purchase as completed and enroll student."""
        purchase.status = Purchase.Status.COMPLETED
        purchase.gateway_transaction_id = gateway_transaction_id
        purchase.gateway_response = gateway_response or {}
        purchase.save()
        Enrollment.objects.get_or_create(
            student=purchase.user,
            course=purchase.course,
        )
        return purchase