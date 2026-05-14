from django.contrib import admin
from battle.models import BattleQuestion, BattleRoom, BattleSubmission

# @admin.register(BattleQuestion)
# class BattleQuestionAdmin(admin.ModelAdmin):
#     list_display = ['id', 'question', 'order']

admin.site.register(BattleSubmission)
admin.site.register(BattleRoom)
admin.site.register(BattleQuestion)
