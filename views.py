from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .badge_engine import assign_badges
from .forms import EvaluationForm, PaperForm
from .models import ActivityLog, ChatMessage, Paper, Profile, ResearchCategory, SupervisorRequest, PaperComment
from .risk_engine import get_papers_with_risk


DEFAULT_CATEGORIES = [
    ('Artificial Intelligence', 'AI, machine learning, data mining, and automation.'),
    ('Software Engineering', 'Software design, testing, architecture, and process.'),
    ('Cybersecurity', 'Security, privacy, cryptography, and digital forensics.'),
    ('Data Science', 'Analytics, visualization, and applied statistics.'),
    ('Human Computer Interaction', 'Usability, UX research, and interaction design.'),
]


def ensure_default_categories():
    for name, description in DEFAULT_CATEGORIES:
        ResearchCategory.objects.get_or_create(name=name, defaults={'description': description})


def user_role(user):
    if not user.is_authenticated or not hasattr(user, 'profile'):
        return None
    return user.profile.role


def update_student_profile(student):
    papers = Paper.objects.filter(student=student)
    score = round(papers.aggregate(avg=Avg('final_score'))['avg'] or 0, 2)
    profile = student.profile
    profile.research_score = score
    if score >= 85:
        profile.reputation_level = 'Elite Researcher'
    elif score >= 70:
        profile.reputation_level = 'Advanced Researcher'
    elif score >= 50:
        profile.reputation_level = 'Active Researcher'
    elif score >= 25:
        profile.reputation_level = 'Emerging Researcher'
    else:
        profile.reputation_level = 'Beginner'
    profile.save()


def log_activity(user, action, paper=None, detail=''):
    ActivityLog.objects.create(user=user, paper=paper, action=action, detail=detail)


def get_pending_supervisor_request(student):
    return SupervisorRequest.objects.filter(student=student, status='pending').select_related('supervisor').first()


def home(request):
    ensure_default_categories()
    supervisors = User.objects.filter(profile__role='supervisor').select_related('profile')
    selected_supervisor = None
    supervisor_request = None
    approved_supervisor = None
    can_select_supervisor = False
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        can_select_supervisor = request.user.profile.role == 'student'
        if can_select_supervisor:
            approved_supervisor = request.user.profile.approved_supervisor
            if approved_supervisor:
                selected_supervisor = approved_supervisor
            else:
                supervisor_request = get_pending_supervisor_request(request.user)
                if supervisor_request:
                    selected_supervisor = supervisor_request.supervisor
    return render(request, 'home.html', {
        'supervisors': supervisors,
        'can_select_supervisor': can_select_supervisor,
        'selected_supervisor': selected_supervisor,
        'supervisor_request': supervisor_request,
        'approved_supervisor': approved_supervisor,
    })


@login_required
def select_supervisor(request):
    if request.method != 'POST':
        return redirect('home')
    if user_role(request.user) != 'student':
        messages.error(request, 'Only student users can request a supervisor.')
        return redirect('home')

    supervisor = User.objects.filter(
        id=request.POST.get('supervisor_id'),
        profile__role='supervisor',
    ).first()
    if not supervisor:
        messages.error(request, 'Supervisor not found.')
        return redirect('home')

    if request.user.profile.approved_supervisor == supervisor:
        messages.info(request, 'You already have approval from this supervisor.')
        return redirect('home')

    pending_request = get_pending_supervisor_request(request.user)
    if pending_request and pending_request.supervisor == supervisor:
        messages.info(request, f'Your request is already pending with {supervisor.username}.')
        return redirect('home')

    if pending_request:
        pending_request.status = 'rejected'
        pending_request.rejected_at = timezone.now()
        pending_request.save()

    SupervisorRequest.objects.create(student=request.user, supervisor=supervisor)
    log_activity(request.user, 'Supervisor request created', detail=f'Requested approval from {supervisor.username}.')
    messages.success(request, f'Request sent to {supervisor.username}. Await approval before working under them.')
    return redirect('home')


@login_required
def approve_supervisor_request(request, request_id):
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('dashboard')
    supervisor_request = get_object_or_404(SupervisorRequest, id=request_id)
    if supervisor_request.supervisor != request.user or supervisor_request.status != 'pending':
        messages.error(request, 'You do not have permission to approve this request.')
        return redirect('dashboard')

    supervisor_request.status = 'approved'
    supervisor_request.approved_at = timezone.now()
    supervisor_request.save()

    student_profile = supervisor_request.student.profile
    student_profile.approved_supervisor = request.user
    student_profile.save()

    SupervisorRequest.objects.filter(student=supervisor_request.student, status='pending').exclude(id=supervisor_request.id).update(status='rejected', rejected_at=timezone.now())
    log_activity(request.user, 'Supervisor request approved', detail=f'Approved {supervisor_request.student.username} to work under you.')
    messages.success(request, f'You have approved {supervisor_request.student.username} as your student.')
    return redirect('dashboard')


@login_required
def reject_supervisor_request(request, request_id):
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('dashboard')
    supervisor_request = get_object_or_404(SupervisorRequest, id=request_id)
    if supervisor_request.supervisor != request.user or supervisor_request.status != 'pending':
        messages.error(request, 'You do not have permission to reject this request.')
        return redirect('dashboard')

    supervisor_request.status = 'rejected'
    supervisor_request.rejected_at = timezone.now()
    supervisor_request.save()
    log_activity(request.user, 'Supervisor request rejected', detail=f'Rejected {supervisor_request.student.username} request.')
    messages.error(request, f'You rejected the supervision request from {supervisor_request.student.username}.')
    return redirect('dashboard')


def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip().lower()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        role = request.POST.get('role', 'student')
        email = request.POST.get('email', '').strip().lower()

        if not username or not password1 or not password2:
            messages.error(request, 'Please fill out all required fields.')
            return redirect('signup')
        if role not in dict(Profile.ROLE_CHOICES):
            messages.error(request, 'Please choose a valid account role.')
            return redirect('signup')
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return redirect('signup')
        if len(password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('signup')
        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('signup')

        user = User.objects.create_user(username=username, email=email or '', password=password1)
        Profile.objects.create(user=user, role=role)
        messages.success(request, 'Account created successfully. Please log in.')
        return redirect('login')
    return render(request, 'signup.html')


def custom_login(request):
    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        selected_role = request.POST.get('role', '').strip()
        user = authenticate(request, username=identifier, password=password)
        if not user and identifier:
            fallback_user = User.objects.filter(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            ).first()
            if fallback_user:
                user = authenticate(request, username=fallback_user.username, password=password)
        if user:
            if not hasattr(user, 'profile'):
                messages.error(request, 'Your account is missing a profile role. Please contact support.')
            elif selected_role and user.profile.role != selected_role:
                messages.error(request, 'Please sign in with the correct role for your account.')
            else:
                login(request, user)
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username/email or password.')
    return render(request, 'login.html')


def custom_logout(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    role = user_role(request.user)
    if role == 'student':
        papers = Paper.objects.filter(student=request.user).select_related('supervisor', 'category', 'journal_index').order_by('-created_at')
        papers_with_risk = get_papers_with_risk(papers)
        supervisors = User.objects.filter(profile__role='supervisor').select_related('profile')
        approved_supervisor = request.user.profile.approved_supervisor
        supervisor_request = None
        selected_supervisor = None
        if approved_supervisor:
            selected_supervisor = approved_supervisor
        else:
            supervisor_request = get_pending_supervisor_request(request.user)
            if supervisor_request:
                selected_supervisor = supervisor_request.supervisor
        can_select_supervisor = True
        return render(request, 'dashboard/student_dashboard.html', {
            'papers': papers,
            'papers_with_risk': papers_with_risk,
            'profile': request.user.profile,
            'achievements': request.user.achievements.all()[:6],
            'recent_activities': request.user.activity_logs.select_related('paper')[:8],
            'submitted_count': papers.filter(status='submitted').count(),
            'approved_count': papers.filter(status='approved').count(),
            'revision_count': papers.filter(status='needs_revision').count(),
            'overdue_count': sum(1 for paper in papers if paper.deadline_status == 'overdue'),
            'supervisors': supervisors,
            'selected_supervisor': selected_supervisor,
            'can_select_supervisor': can_select_supervisor,
            'supervisor_request': supervisor_request,
            'approved_supervisor': approved_supervisor,
        })

    if role == 'supervisor':
        papers = Paper.objects.filter(supervisor=request.user).select_related('student', 'category', 'journal_index').order_by('-created_at')
        papers_with_risk = get_papers_with_risk(papers)
        at_risk_papers = [pr for pr in papers_with_risk if pr[1]['level'] in ('high', 'medium')]
        
        students = User.objects.filter(profile__approved_supervisor=request.user).distinct()
        
        approved_count = papers.filter(status='approved').count()
        rejected_count = papers.filter(status='rejected').count()
        reviewed_total = approved_count + rejected_count
        acceptance_rate = round((approved_count / reviewed_total) * 100) if reviewed_total else 0
        journal_stats = papers.exclude(journal='').values('journal').annotate(paper_count=Count('id')).order_by('-paper_count')[:6]
        supervisor_requests = SupervisorRequest.objects.filter(supervisor=request.user, status='pending').select_related('student')
        return render(request, 'dashboard/supervisor_dashboard.html', {
            'papers': papers,
            'papers_with_risk': papers_with_risk,
            'at_risk_papers': at_risk_papers,
            'profile': request.user.profile,
            'pending_count': papers.filter(status='submitted').count(),
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'revision_count': papers.filter(status='needs_revision').count(),
            'acceptance_rate': acceptance_rate,
            'overdue_count': sum(1 for paper in papers if paper.deadline_status == 'overdue'),
            'journal_stats': journal_stats,
            'students': students,
            'supervisor_requests': supervisor_requests,
        })

    if role == 'admin':
        papers = Paper.objects.select_related('student', 'supervisor', 'category')
        return render(request, 'dashboard/admin_dashboard.html', {
            'profile': request.user.profile,
            'total_users': User.objects.count(),
            'students': User.objects.filter(profile__role='student').count(),
            'supervisors': User.objects.filter(profile__role='supervisor').count(),
            'total_papers': papers.count(),
            'approved_papers': papers.filter(status='approved').count(),
            'rejected_papers': papers.filter(status='rejected').count(),
            'pending_papers': papers.filter(status='submitted').count(),
            'revision_papers': papers.filter(status='needs_revision').count(),
            'active_researchers': papers.values('student').distinct().count(),
            'avg_score': round(papers.aggregate(avg=Avg('final_score'))['avg'] or 0, 2),
            'recent_papers': papers.order_by('-created_at')[:8],
            'category_stats': papers.values('category__name').annotate(paper_count=Count('id')).order_by('-paper_count')[:8],
            'activities': ActivityLog.objects.select_related('user', 'paper')[:10],
        })

    messages.error(request, 'Your account profile is incomplete.')
    return redirect('home')


@login_required
def profile(request):
    role = user_role(request.user)
    if role == 'student':
        papers = Paper.objects.filter(student=request.user)
    elif role == 'supervisor':
        papers = Paper.objects.filter(supervisor=request.user)
    else:
        papers = Paper.objects.none()
    return render(request, 'profile.html', {
        'profile': request.user.profile,
        'papers': papers,
        'achievements': request.user.achievements.all(),
        'can_edit_profile': True,
    })


@login_required
def view_profile(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = getattr(user, 'profile', None)
    if profile and profile.role == 'student':
        papers = Paper.objects.filter(student=user)
    elif profile and profile.role == 'supervisor':
        papers = Paper.objects.filter(supervisor=user)
    else:
        papers = Paper.objects.none()
    achievements = user.achievements.all() if hasattr(user, 'achievements') else []
    can_edit_profile = request.user == user
    return render(request, 'profile.html', {
        'user': user,
        'profile': profile,
        'papers': papers,
        'achievements': achievements,
        'can_edit_profile': can_edit_profile,
    })


@login_required
def settings(request):
    if request.method == 'POST':
        request.user.email = request.POST.get('email', '').strip()
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.save()
        messages.success(request, 'Settings updated successfully.')
        return redirect('settings')
    return render(request, 'settings.html', {'profile': request.user.profile})


@login_required
def add_paper(request):
    if user_role(request.user) != 'student':
        messages.error(request, 'Only students can upload research papers.')
        return redirect('dashboard')

    if not request.user.profile.approved_supervisor:
        messages.error(request, 'Please wait for supervisor approval before adding papers.')
        return redirect('dashboard')

    ensure_default_categories()
    approved_supervisor = request.user.profile.approved_supervisor
    if request.method == 'POST':
        form = PaperForm(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data.get('supervisor') and form.cleaned_data['supervisor'] != approved_supervisor:
                form.add_error('supervisor', 'Please use your approved supervisor for this paper.')
            else:
                paper = form.save(commit=False)
                paper.student = request.user
                paper.supervisor = approved_supervisor
                paper.save()
                log_activity(request.user, 'Paper uploaded', paper, 'A new research paper was added as draft.')
                messages.success(request, 'Paper uploaded successfully.')
                return redirect('dashboard')
    else:
        form = PaperForm(initial={'supervisor': approved_supervisor.id if approved_supervisor else None})
        if approved_supervisor:
            form.fields['supervisor'].queryset = User.objects.filter(id=approved_supervisor.id)
            form.fields['supervisor'].disabled = True
    return render(request, 'add_paper.html', {'form': form})


@login_required
def edit_paper(request, paper_id):
    paper = get_object_or_404(Paper, id=paper_id, student=request.user)
    if paper.status == 'approved':
        messages.error(request, 'Approved papers cannot be edited.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = PaperForm(request.POST, request.FILES, instance=paper)
        if form.is_valid():
            paper = form.save(commit=False)
            paper.revision_count += 1
            paper.status = 'draft'
            paper.save()
            log_activity(request.user, 'Paper revised', paper, 'Student updated the paper after feedback.')
            messages.success(request, 'Paper updated successfully. Submit it when ready for review.')
            return redirect('dashboard')
    else:
        form = PaperForm(instance=paper)
    return render(request, 'edit_paper.html', {'form': form, 'paper': paper})


@login_required
def submit_paper(request, paper_id):
    paper = get_object_or_404(Paper, id=paper_id, student=request.user)
    if not paper.supervisor:
        messages.error(request, 'Please select a supervisor before submitting.')
        return redirect('edit_paper', paper_id=paper.id)
    if request.user.profile.approved_supervisor != paper.supervisor:
        messages.error(request, 'Paper submission requires your approved supervisor.')
        return redirect('edit_paper', paper_id=paper.id)
    paper.status = 'submitted'
    paper.submitted_at = timezone.now()
    paper.save()
    log_activity(request.user, 'Paper submitted', paper, 'Paper sent to supervisor for review.')
    messages.success(request, 'Paper submitted successfully.')
    return redirect('dashboard')


@login_required
def approve_paper(request, paper_id):
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('dashboard')
    paper = get_object_or_404(Paper, id=paper_id)
    if user_role(request.user) not in ['supervisor', 'admin'] or (user_role(request.user) == 'supervisor' and paper.supervisor != request.user):
        messages.error(request, 'You do not have permission to approve this paper.')
        return redirect('dashboard')
    paper.status = 'approved'
    paper.submitted_at = paper.submitted_at or timezone.now()
    paper.save()
    update_student_profile(paper.student)
    assign_badges(paper.student, paper)
    log_activity(request.user, 'Paper approved', paper, 'Supervisor marked the paper as approved.')
    messages.success(request, 'Paper approved.')
    return redirect('dashboard')


@login_required
def reject_paper(request, paper_id):
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('dashboard')
    paper = get_object_or_404(Paper, id=paper_id)
    if user_role(request.user) not in ['supervisor', 'admin'] or (user_role(request.user) == 'supervisor' and paper.supervisor != request.user):
        messages.error(request, 'You do not have permission to reject this paper.')
        return redirect('dashboard')
    paper.status = 'rejected'
    paper.save()
    update_student_profile(paper.student)
    log_activity(request.user, 'Paper rejected', paper, 'Supervisor rejected the paper.')
    messages.error(request, 'Paper rejected.')
    return redirect('dashboard')


@login_required
def request_revision(request, paper_id):
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('dashboard')
    paper = get_object_or_404(Paper, id=paper_id)
    if user_role(request.user) not in ['supervisor', 'admin'] or (user_role(request.user) == 'supervisor' and paper.supervisor != request.user):
        messages.error(request, 'You do not have permission to request revision.')
        return redirect('dashboard')
    paper.status = 'needs_revision'
    paper.revision_count = (paper.revision_count or 0) + 1
    paper.save()
    log_activity(request.user, 'Revision requested', paper, 'Supervisor requested another research revision.')
    messages.success(request, 'Revision requested.')
    return redirect('dashboard')


@login_required
def evaluate_paper(request, paper_id):
    paper = get_object_or_404(Paper, id=paper_id)
    if user_role(request.user) not in ['supervisor', 'admin'] or (user_role(request.user) == 'supervisor' and paper.supervisor != request.user):
        messages.error(request, 'You do not have permission to evaluate this paper.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = EvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.paper = paper
            evaluation.reviewer = request.user
            evaluation.save()

            paper.previous_score = paper.current_score
            paper.current_score = evaluation.total_score()
            paper.evaluation = evaluation.feedback
            paper.status = 'needs_revision' if 'revision' in evaluation.feedback.lower() else paper.status
            paper.save()
            update_student_profile(paper.student)
            assign_badges(paper.student, paper)
            log_activity(request.user, 'Paper evaluated', paper, f'New quality score: {paper.current_score}.')
            messages.success(request, 'Evaluation submitted successfully.')
            return redirect('dashboard')
    else:
        form = EvaluationForm()

    previous_evaluations = paper.evaluations.select_related('reviewer').order_by('-created_at')
    return render(request, 'evaluate_paper.html', {
        'form': form,
        'paper': paper,
        'previous_evaluations': previous_evaluations,
    })


@login_required
def supervisor_student_detail(request, student_id):
    if user_role(request.user) not in ['supervisor', 'admin']:
        messages.error(request, 'You do not have permission to view this.')
        return redirect('dashboard')
    
    student = get_object_or_404(User, id=student_id, profile__role='student')
    if user_role(request.user) == 'supervisor' and student.profile.approved_supervisor != request.user:
        messages.error(request, 'You do not have permission to view this student.')
        return redirect('dashboard')
    
    papers = Paper.objects.filter(student=student).select_related('supervisor', 'category', 'journal_index').order_by('-created_at')
    papers_with_risk = get_papers_with_risk(papers)
    
    avg_score = round(papers.aggregate(avg=Avg('final_score'))['avg'] or 0, 2)
    submitted_count = papers.filter(status__in=['submitted', 'needs_revision', 'approved', 'rejected']).count()
    on_time = 0
    for p in papers:
        if p.deadline and p.submitted_at and p.submitted_at <= p.deadline:
            on_time += 1
    compliance_rate = round((on_time / submitted_count) * 100) if submitted_count else 0
    
    return render(request, 'dashboard/supervisor_student_detail.html', {
        'student': student,
        'papers_with_risk': papers_with_risk,
        'avg_score': avg_score,
        'compliance_rate': compliance_rate,
        'papers_count': papers.count(),
    })


@login_required
def chat_with_user(request, user_id):
    # Fetch the other user
    other_user = get_object_or_404(User, id=user_id)
    
    # Check profiles exist
    if not hasattr(request.user, 'profile'):
        messages.error(request, 'Your profile is incomplete. Please contact support.')
        return redirect('dashboard')
    
    if not hasattr(other_user, 'profile'):
        messages.error(request, 'The user\'s profile is incomplete.')
        return redirect('dashboard')

    # Permission check: prevent self-chat
    if request.user == other_user:
        messages.error(request, 'You cannot chat with yourself.')
        return redirect('dashboard')

    # Permission check: verify relationship
    allowed = False
    reason = ''
    
    current_user_role = request.user.profile.role
    other_user_role = other_user.profile.role
    
    # Allow if request.user is a student and other_user is their approved supervisor
    if current_user_role == 'student' and other_user_role == 'supervisor':
        if request.user.profile.approved_supervisor == other_user:
            allowed = True
        else:
            reason = 'This is not your approved supervisor.'
    
    # Allow if request.user is a supervisor and other_user is their approved student
    elif current_user_role == 'supervisor' and other_user_role == 'student':
        if other_user.profile.approved_supervisor == request.user:
            allowed = True
        else:
            reason = f'This student ({other_user.username}) is not your approved student. Their supervisor is: {other_user.profile.approved_supervisor}'
    
    # Deny all other combinations
    else:
        reason = 'Only approved supervisor-student pairs can chat.'

    if not allowed:
        error_msg = f'You do not have permission to chat with this user. {reason}'.strip()
        messages.error(request, error_msg)
        return redirect('dashboard')

    # Handle message submission
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        if message_text:
            ChatMessage.objects.create(sender=request.user, receiver=other_user, text=message_text)
            messages.success(request, 'Message sent!')
            return redirect('chat_with_user', user_id=user_id)
        else:
            messages.error(request, 'Please enter a message.')

    # Fetch all messages between the two users
    messages_list = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).select_related('sender', 'receiver').order_by('created_at')

    return render(request, 'chat.html', {
        'other_user': other_user,
        'messages_list': messages_list,
    })


@login_required
def paper_detail(request, paper_id):
    paper = get_object_or_404(Paper, id=paper_id)
    # Check permissions
    if user_role(request.user) == 'student' and paper.student != request.user:
        messages.error(request, 'You do not have permission to view this paper.')
        return redirect('dashboard')
    if user_role(request.user) == 'supervisor' and paper.supervisor != request.user:
        messages.error(request, 'You do not have permission to view this paper.')
        return redirect('dashboard')
    
    comments = paper.comments.select_related('author').all()
    evaluations = paper.evaluations.select_related('reviewer').order_by('-created_at')
    
    return render(request, 'paper_detail.html', {
        'paper': paper,
        'comments': comments,
        'evaluations': evaluations,
        'role': user_role(request.user),
    })


@login_required
def add_comment(request, paper_id):
    if request.method == 'POST':
        paper = get_object_or_404(Paper, id=paper_id)
        if (user_role(request.user) == 'student' and paper.student == request.user) or \
           (user_role(request.user) == 'supervisor' and paper.supervisor == request.user) or \
           (user_role(request.user) == 'admin'):
            text = request.POST.get('text', '').strip()
            if text:
                PaperComment.objects.create(paper=paper, author=request.user, text=text)
                messages.success(request, 'Comment added successfully.')
            else:
                messages.error(request, 'Comment cannot be empty.')
        else:
            messages.error(request, 'You do not have permission to comment on this paper.')
    return redirect('paper_detail', paper_id=paper_id)
