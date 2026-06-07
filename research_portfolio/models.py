from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from .validators import validate_pdf


class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('supervisor', 'Supervisor'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    research_score = models.FloatField(default=0.0)
    reputation_level = models.CharField(max_length=50, default='Beginner')
    approved_supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_students',
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}: {self.text[:50]}"


class SupervisorRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='supervisor_requests')
    supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='supervisor_requests_received')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['student', 'supervisor', 'status'], name='unique_student_supervisor_status')
        ]

    def __str__(self):
        return f"{self.student.username} -> {self.supervisor.username} ({self.status})"


class JournalIndex(models.Model):
    name = models.CharField(max_length=100, unique=True)
    indexing_type = models.CharField(max_length=50, blank=True)
    impact_factor = models.FloatField(default=0.0)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.name


class ResearchCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Paper(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('needs_revision', 'Needs Revision'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    title = models.CharField(max_length=200)
    authors = models.CharField(max_length=300, blank=True)
    journal = models.CharField(max_length=200, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    doi = models.CharField(max_length=100, blank=True)
    abstract = models.TextField(blank=True)

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_papers')
    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_papers',
    )
    category = models.ForeignKey(ResearchCategory, on_delete=models.SET_NULL, null=True, blank=True)
    journal_index = models.ForeignKey(JournalIndex, on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    evaluation = models.TextField(blank=True)

    pdf = models.FileField(upload_to='papers/', null=True, blank=True, validators=[validate_pdf])
    deadline = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    current_score = models.FloatField(default=0.0)
    previous_score = models.FloatField(default=0.0)
    improvement_bonus = models.FloatField(default=0.0)
    consistency_score = models.FloatField(default=0.0)
    collaboration_score = models.FloatField(default=0.0)
    impact_score = models.FloatField(default=0.0)
    final_score = models.FloatField(default=0.0)
    revision_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_improvement_bonus(self):
        difference = self.current_score - self.previous_score
        if difference > 0:
            return min(difference * 2, 100)
        return 0

    def calculate_consistency_score(self):
        score = 40
        if self.submitted_at:
            score += 25
        if self.deadline and self.submitted_at and self.submitted_at <= self.deadline:
            score += 25
        if self.revision_count:
            score += min(self.revision_count * 5, 10)
        return min(score, 100)

    def calculate_collaboration_score(self):
        author_count = len([author.strip() for author in self.authors.split(',') if author.strip()])
        if author_count >= 3:
            return 100
        if author_count == 2:
            return 70
        return 35 if author_count == 1 else 0

    def calculate_impact_score(self):
        if self.status == 'approved':
            return 100
        if self.status == 'submitted':
            return 55
        if self.status == 'needs_revision':
            return 35
        return 10 if self.status == 'draft' else 0

    def calculate_final_score(self):
        self.improvement_bonus = self.calculate_improvement_bonus()
        self.consistency_score = self.calculate_consistency_score()
        self.collaboration_score = self.calculate_collaboration_score()
        self.impact_score = self.calculate_impact_score()
        self.final_score = round(
            (0.40 * self.current_score)
            + (0.25 * self.improvement_bonus)
            + (0.15 * self.consistency_score)
            + (0.10 * self.collaboration_score)
            + (0.10 * self.impact_score),
            2,
        )
        return self.final_score

    @property
    def deadline_status(self):
        if not self.deadline:
            return 'none'
        now = timezone.now()
        if self.deadline < now and self.status not in ['approved', 'rejected']:
            return 'overdue'
        remaining_days = (self.deadline - now).days
        if remaining_days <= 3:
            return 'urgent'
        if remaining_days <= 7:
            return 'nearing'
        return 'safe'

    def save(self, *args, **kwargs):
        self.calculate_final_score()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Evaluation(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='evaluations')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    methodology_score = models.IntegerField(default=0)
    innovation_score = models.IntegerField(default=0)
    writing_score = models.IntegerField(default=0)
    technical_score = models.IntegerField(default=0)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_score(self):
        return round(
            (
                self.methodology_score
                + self.innovation_score
                + self.writing_score
                + self.technical_score
            )
            / 4,
            2,
        )

    def __str__(self):
        return f"Evaluation for {self.paper.title}"


class Achievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'title'], name='unique_user_achievement'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    paper = models.ForeignKey(
        Paper,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    action = models.CharField(max_length=100)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.action}"

class PaperComment(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.paper.title}"

