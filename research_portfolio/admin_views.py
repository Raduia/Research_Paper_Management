from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import ActivityLog, JournalIndex, Paper, Profile, ResearchCategory


def _admin_required(request):
    """Check if the current user is an admin. Returns True if admin, False otherwise."""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        messages.error(request, 'You do not have permission to access the admin panel.')
        return False
    return True


@login_required
def admin_users(request):
    """List all users with profiles, paper counts. Supports search via ?q= param."""
    if not _admin_required(request):
        return redirect('dashboard')

    query = request.GET.get('q', '').strip()
    all_users = User.objects.select_related('profile').all()

    if query:
        all_users = all_users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )

    users = []
    for u in all_users:
        profile = getattr(u, 'profile', None)
        paper_count = Paper.objects.filter(student=u).count()
        users.append({
            'user': u,
            'profile': profile,
            'paper_count': paper_count,
            'is_active': u.is_active,
        })

    return render(request, 'admin_panel/admin_users.html', {
        'users': users,
        'query': query,
    })


@login_required
def admin_edit_user(request, user_id):
    """GET: show edit form. POST: update role, first_name, last_name, email, is_active."""
    if not _admin_required(request):
        return redirect('dashboard')

    target_user = get_object_or_404(User, id=user_id)
    profile = getattr(target_user, 'profile', None)

    if request.method == 'POST':
        target_user.first_name = request.POST.get('first_name', '').strip()
        target_user.last_name = request.POST.get('last_name', '').strip()
        target_user.email = request.POST.get('email', '').strip()
        target_user.is_active = request.POST.get('is_active') == 'on'
        target_user.save()

        if profile:
            new_role = request.POST.get('role', profile.role)
            if new_role in dict(Profile.ROLE_CHOICES):
                profile.role = new_role
                profile.save()

        messages.success(request, f'User "{target_user.username}" updated successfully.')
        return redirect('admin_users')

    return render(request, 'admin_panel/admin_edit_user.html', {
        'target_user': target_user,
        'profile': profile,
        'role_choices': Profile.ROLE_CHOICES,
    })


@login_required
def admin_delete_user(request, user_id):
    """POST only: deactivate user (set is_active=False)."""
    if not _admin_required(request):
        return redirect('dashboard')

    if request.method != 'POST':
        return redirect('admin_users')

    target_user = get_object_or_404(User, id=user_id)
    target_user.is_active = False
    target_user.save()
    messages.success(request, f'User "{target_user.username}" has been deactivated.')
    return redirect('admin_users')


@login_required
def admin_system_settings(request):
    """GET: show categories list + DB stats. POST: add new category (name, description)."""
    if not _admin_required(request):
        return redirect('dashboard')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if name:
            if ResearchCategory.objects.filter(name__iexact=name).exists():
                messages.error(request, f'Category "{name}" already exists.')
            else:
                ResearchCategory.objects.create(name=name, description=description)
                messages.success(request, f'Category "{name}" created successfully.')
        else:
            messages.error(request, 'Category name is required.')
        return redirect('admin_system_settings')

    categories = ResearchCategory.objects.all().order_by('name')
    total_papers = Paper.objects.count()
    total_users = User.objects.count()

    # Basic DB size info
    db_size_info = {
        'papers': total_papers,
        'users': total_users,
        'categories': categories.count(),
        'evaluations': Paper.objects.aggregate(count=Count('evaluations'))['count'] or 0,
        'activity_logs': ActivityLog.objects.count(),
    }

    return render(request, 'admin_panel/admin_system_settings.html', {
        'categories': categories,
        'total_papers': total_papers,
        'total_users': total_users,
        'db_size_info': db_size_info,
    })


@login_required
def admin_delete_category(request, category_id):
    """POST only: delete category."""
    if not _admin_required(request):
        return redirect('dashboard')

    if request.method != 'POST':
        return redirect('admin_system_settings')

    category = get_object_or_404(ResearchCategory, id=category_id)
    category_name = category.name
    category.delete()
    messages.success(request, f'Category "{category_name}" deleted successfully.')
    return redirect('admin_system_settings')


@login_required
def admin_all_papers(request):
    """GET: list all papers with search (?q=) and status filter (?status=)."""
    if not _admin_required(request):
        return redirect('dashboard')

    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    papers = Paper.objects.select_related('student', 'supervisor', 'category').order_by('-created_at')

    if query:
        papers = papers.filter(
            Q(title__icontains=query)
            | Q(authors__icontains=query)
            | Q(journal__icontains=query)
            | Q(student__username__icontains=query)
            | Q(supervisor__username__icontains=query)
        )

    if status_filter:
        papers = papers.filter(status=status_filter)

    status_choices = Paper.STATUS_CHOICES

    return render(request, 'admin_panel/admin_all_papers.html', {
        'papers': papers,
        'query': query,
        'status_filter': status_filter,
        'status_choices': status_choices,
    })


@login_required
def research_clusters(request):
    """GET: show research area clustering with category, journal, and index stats."""
    if not _admin_required(request):
        return redirect('dashboard')

    # Category stats: category name, paper_count, avg_score, journals list
    categories = ResearchCategory.objects.all()
    category_stats = []
    for cat in categories:
        cat_papers = Paper.objects.filter(category=cat)
        paper_count = cat_papers.count()
        avg_score = round(cat_papers.aggregate(avg=Avg('final_score'))['avg'] or 0, 2)
        journals = list(
            cat_papers.exclude(journal='')
            .values_list('journal', flat=True)
            .distinct()
        )
        category_stats.append({
            'name': cat.name,
            'paper_count': paper_count,
            'avg_score': avg_score,
            'journals': journals,
        })

    # Journal stats: journal name, paper_count, categories list
    journal_qs = (
        Paper.objects.exclude(journal='')
        .values('journal')
        .annotate(paper_count=Count('id'))
        .order_by('-paper_count')
    )
    journal_stats = []
    for entry in journal_qs:
        journal_name = entry['journal']
        cat_names = list(
            Paper.objects.filter(journal=journal_name)
            .exclude(category__isnull=True)
            .values_list('category__name', flat=True)
            .distinct()
        )
        journal_stats.append({
            'name': journal_name,
            'paper_count': entry['paper_count'],
            'categories': cat_names,
        })

    # Index stats: index name, paper count
    index_stats = []
    for idx in JournalIndex.objects.all():
        paper_count = Paper.objects.filter(journal_index=idx).count()
        index_stats.append({
            'name': str(idx),
            'paper_count': paper_count,
        })

    return render(request, 'admin_panel/research_clusters.html', {
        'category_stats': category_stats,
        'journal_stats': journal_stats,
        'index_stats': index_stats,
    })
