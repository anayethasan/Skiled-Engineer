from django.contrib import admin
from analytics.models import CoursesAnalytics, MistakeAnalysis, MistakeLog, Purchase

admin.site.register(CoursesAnalytics)
admin.site.register(MistakeAnalysis)
admin.site.register(MistakeLog)
admin.site.register(Purchase)
