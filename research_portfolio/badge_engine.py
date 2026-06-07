from .models import Achievement


def award_once(user, title, description):
    Achievement.objects.get_or_create(
        user=user,
        title=title,
        defaults={'description': description},
    )


def assign_badges(user, paper):
    if paper.improvement_bonus >= 70:
        award_once(
            user,
            'Outstanding Comeback',
            'Recovered strongly after feedback and showed major research improvement.',
        )

    if paper.final_score >= 85:
        award_once(
            user,
            'Elite Researcher',
            'Achieved an elite final research score.',
        )

    if paper.status == 'approved':
        award_once(
            user,
            'Publication Ready',
            'Completed the review workflow and reached approval.',
        )

    if paper.revision_count >= 3:
        award_once(
            user,
            'Persistent Improver',
            'Completed multiple research revisions with consistent effort.',
        )
