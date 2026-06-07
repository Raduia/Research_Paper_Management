from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.conf import settings
from django.conf.urls.static import static

from . import views, admin_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('signup/', views.signup, name='signup'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),

    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('select-supervisor/', views.select_supervisor, name='select_supervisor'),
    path('supervisor-request/<int:request_id>/approve/', views.approve_supervisor_request, name='approve_supervisor_request'),
    path('supervisor-request/<int:request_id>/reject/', views.reject_supervisor_request, name='reject_supervisor_request'),

    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings, name='settings'),

    path('add-paper/', views.add_paper, name='add_paper'),
    path('edit-paper/<int:paper_id>/', views.edit_paper, name='edit_paper'),

    path('submit-paper/<int:paper_id>/', views.submit_paper, name='submit_paper'),
    path('approve-paper/<int:paper_id>/', views.approve_paper, name='approve_paper'),
    path('reject-paper/<int:paper_id>/', views.reject_paper, name='reject_paper'),
    path('request-revision/<int:paper_id>/', views.request_revision, name='request_revision'),
    path('evaluate-paper/<int:paper_id>/', views.evaluate_paper, name='evaluate_paper'),
    path('paper-detail/<int:paper_id>/', views.paper_detail, name='paper_detail'),
    path('paper-detail/<int:paper_id>/comment/', views.add_comment, name='add_comment'),

    path('admin-panel/users/', admin_views.admin_users, name='admin_users'),
    path('admin-panel/users/<int:user_id>/edit/', admin_views.admin_edit_user, name='admin_edit_user'),
    path('admin-panel/users/<int:user_id>/delete/', admin_views.admin_delete_user, name='admin_delete_user'),
    path('admin-panel/settings/', admin_views.admin_system_settings, name='admin_system_settings'),
    path('admin-panel/settings/category/<int:category_id>/delete/', admin_views.admin_delete_category, name='admin_delete_category'),
    path('admin-panel/papers/', admin_views.admin_all_papers, name='admin_all_papers'),
    path('admin-panel/clusters/', admin_views.research_clusters, name='research_clusters'),
    path('users/<int:user_id>/', views.view_profile, name='user_profile'),
    path('chat/<int:user_id>/', views.chat_with_user, name='chat_with_user'),

    path('supervisor/student/<int:student_id>/', views.supervisor_student_detail, name='supervisor_student_detail'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Include Django auth views (password change/reset) at root so templates can reverse named URLs
urlpatterns += [
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='password_change.html'), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='password_change_done.html'), name='password_change_done'),
    path('', include('django.contrib.auth.urls')),
]
