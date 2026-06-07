from django.contrib import admin

from .models import Achievement, ActivityLog, ChatMessage, Evaluation, JournalIndex, Paper, Profile, ResearchCategory


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'research_score', 'reputation_level')
    list_filter = ('role', 'reputation_level')
    search_fields = ('user__username', 'user__email')


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'supervisor', 'status', 'current_score', 'final_score', 'revision_count')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'authors', 'journal', 'student__username', 'supervisor__username')
    readonly_fields = ('final_score', 'improvement_bonus', 'consistency_score', 'collaboration_score', 'impact_score')


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('paper', 'reviewer', 'total_score', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('paper__title', 'reviewer__username', 'feedback')


@admin.register(ResearchCategory)
class ResearchCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(JournalIndex)
class JournalIndexAdmin(admin.ModelAdmin):
    list_display = ('name', 'indexing_type', 'impact_factor', 'url')
    search_fields = ('name', 'indexing_type')


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'created_at')
    search_fields = ('user__username', 'title')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'text', 'created_at')
    list_filter = ('created_at', 'sender', 'receiver')
    search_fields = ('sender__username', 'receiver__username', 'text')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'paper', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('user__username', 'paper__title', 'detail')
