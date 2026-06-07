from django.utils import timezone


def assess_risk(paper):
    """
    Assess the submission risk for a given paper.
    Returns a dict with 'level', 'reasons', and 'score'.
    """
    risk_score = 0
    reasons = []

    # No supervisor assigned: +30
    if not paper.supervisor:
        risk_score += 30
        reasons.append('No supervisor assigned')

    # No PDF uploaded: +20
    if not paper.pdf:
        risk_score += 20
        reasons.append('No PDF uploaded')

    # Deadline checks
    now = timezone.now()
    if paper.deadline:
        if paper.deadline < now and paper.status not in ('approved', 'rejected'):
            # Deadline overdue: +40
            risk_score += 40
            reasons.append('Deadline is overdue')
        else:
            remaining_days = (paper.deadline - now).days
            if remaining_days <= 3:
                # Deadline within 3 days (urgent): +25
                risk_score += 25
                reasons.append('Deadline within 3 days (urgent)')
            elif remaining_days <= 7:
                # Deadline within 7 days (nearing): +10
                risk_score += 10
                reasons.append('Deadline within 7 days (nearing)')

    # Status is 'rejected': +20
    if paper.status == 'rejected':
        risk_score += 20
        reasons.append('Paper has been rejected')

    # Status still 'draft' and created > 14 days ago (stale): +15
    if paper.status == 'draft' and paper.created_at:
        days_since_creation = (now - paper.created_at).days
        if days_since_creation > 14:
            risk_score += 15
            reasons.append(f'Draft paper is stale ({days_since_creation} days old)')

    # No abstract: +10
    if not paper.abstract or not paper.abstract.strip():
        risk_score += 10
        reasons.append('No abstract provided')

    # revision_count >= 3 with status still not approved: +15
    if paper.revision_count >= 3 and paper.status != 'approved':
        risk_score += 15
        reasons.append(f'High revision count ({paper.revision_count}) without approval')

    # Determine risk level
    if risk_score >= 50:
        level = 'high'
    elif risk_score >= 25:
        level = 'medium'
    else:
        level = 'low'

    # Cap score at 100
    risk_score = min(risk_score, 100)

    return {
        'level': level,
        'reasons': reasons,
        'score': risk_score,
    }


def get_papers_with_risk(queryset):
    """
    Given a queryset of papers, return a list of (paper, risk_info) tuples.
    """
    result = []
    for paper in queryset:
        risk_info = assess_risk(paper)
        result.append((paper, risk_info))
    return result
