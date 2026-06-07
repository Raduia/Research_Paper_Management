from django.utils import timezone


def get_deadline_status(deadline):
    if not deadline:
        return 'none'

    remaining = (deadline - timezone.now()).days
    if remaining < 0:
        return 'overdue'
    if remaining <= 3:
        return 'urgent'
    if remaining <= 7:
        return 'nearing'
    return 'safe'
