from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Paper, Profile


class ResearchWorkflowTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user('student', password='password123')
        Profile.objects.create(user=self.student, role='student')
        self.supervisor = User.objects.create_user('supervisor', password='password123')
        Profile.objects.create(user=self.supervisor, role='supervisor')
        self.other_supervisor = User.objects.create_user('other', password='password123')
        Profile.objects.create(user=self.other_supervisor, role='supervisor')
        self.paper = Paper.objects.create(
            title='Machine Learning in Education',
            authors='Student, Supervisor',
            journal='Education Tech Journal',
            student=self.student,
            supervisor=self.supervisor,
        )

    def test_student_can_submit_paper(self):
        self.client.login(username='student', password='password123')
        response = self.client.get(reverse('submit_paper', args=[self.paper.id]))
        self.assertRedirects(response, reverse('dashboard'))
        self.paper.refresh_from_db()
        self.assertEqual(self.paper.status, 'submitted')
        self.assertIsNotNone(self.paper.submitted_at)

    def test_assigned_supervisor_can_evaluate_and_update_score(self):
        self.client.login(username='supervisor', password='password123')
        response = self.client.post(reverse('evaluate_paper', args=[self.paper.id]), {
            'methodology_score': 80,
            'innovation_score': 90,
            'writing_score': 70,
            'technical_score': 80,
            'feedback': 'Strong paper. Minor revision suggested.',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.paper.refresh_from_db()
        self.student.profile.refresh_from_db()
        self.assertEqual(self.paper.current_score, 80)
        self.assertGreater(self.paper.final_score, 0)
        self.assertEqual(self.paper.status, 'needs_revision')
        self.assertEqual(self.student.profile.research_score, self.paper.final_score)

    def test_unassigned_supervisor_cannot_evaluate(self):
        self.client.login(username='other', password='password123')
        response = self.client.post(reverse('evaluate_paper', args=[self.paper.id]), {
            'methodology_score': 100,
            'innovation_score': 100,
            'writing_score': 100,
            'technical_score': 100,
            'feedback': 'Unauthorized score.',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.paper.refresh_from_db()
        self.assertEqual(self.paper.current_score, 0)

    def test_approval_awards_publication_badge(self):
        self.paper.current_score = 95
        self.paper.save()
        self.client.login(username='supervisor', password='password123')
        response = self.client.get(reverse('approve_paper', args=[self.paper.id]))
        self.assertRedirects(response, reverse('dashboard'))
        self.paper.refresh_from_db()
        self.assertEqual(self.paper.status, 'approved')
        self.assertTrue(self.student.achievements.filter(title='Publication Ready').exists())
