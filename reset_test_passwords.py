import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'research_portfolio.settings')
django.setup()
from django.contrib.auth.models import User
usernames = ['supervisor', 'tanha islam', 'juthi rahman', 'saklaen supervisor']
for username in usernames:
    try:
        u = User.objects.get(username=username)
        u.set_password('test12345')
        u.save()
        print(f'Password reset for {username}')
    except User.DoesNotExist:
        print(f'No user {username}')
