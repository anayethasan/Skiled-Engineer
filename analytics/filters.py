import django_filters
from analytics.models import MistakeAnalysis, MistakeLog, CoursesAnalytics, Purchase


class MistakeLogFilter(django_filters.FilterSet):
    topic     = django_filters.CharFilter(lookup_expr="icontains")
    from_date = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte") 
    to_date   = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model  = MistakeLog
        fields = {
            "source": ["exact"],
        }


class MistakeAnalysisFilter(django_filters.FilterSet):
    topic        = django_filters.CharFilter(lookup_expr="icontains")
    min_mistakes = django_filters.NumberFilter(field_name="mistake_count", lookup_expr="gte")
    max_mistakes = django_filters.NumberFilter(field_name="mistake_count", lookup_expr="lte")

    class Meta:
        model  = MistakeAnalysis
        fields = {}


class CoursesAnalyticsFilter(django_filters.FilterSet):
    from_date = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    to_date   = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model  = CoursesAnalytics
        fields = {
            "course": ["exact"],
        }


class PurchaseFilter(django_filters.FilterSet):
    from_date = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_date   = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model  = Purchase
        fields = {
            "status": ["exact"],
            "course": ["exact"],
        }