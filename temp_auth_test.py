import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'research_portfolio.settings'
import django
django.setup()
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
print('users', User.objects.count())
for u in User.objects.all():
    print('user', u.username, 'is_active', u.is_active, 'password', u.password)
print('about to auth')
a = authenticate(username='anisha', password='12345612')
print('after auth')
print('authenticate', a)
from django.test import Client
client = Client(HTTP_HOST='127.0.0.1')
print('about to post')
try:
    response = client.post('/login/', {'username': 'anisha', 'password': '12345612', 'role': 'student'})
    print('after post')
    print('status', response.status_code)
    print('redirect', response.url if response.status_code in (301,302) else None)
    print('content includes invalid', b'Invalid username or password' in response.content)
except Exception as e:
    import traceback
    traceback.print_exc()
    print('POST failed', repr(e))
