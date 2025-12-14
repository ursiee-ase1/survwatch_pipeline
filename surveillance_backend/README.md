# Django Surveillance Backend

Django backend for CCTV analytics platform.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Create API token
python manage.py shell
>>> from django.contrib.auth.models import User
>>> from rest_framework.authtoken.models import Token
>>> user = User.objects.first()
>>> token = Token.objects.create(user=user)
>>> print(token.key)

# Run server
python manage.py runserver
```

## Access Points

- **Admin Panel**: http://localhost:8000/admin
- **Dashboard**: http://localhost:8000/dashboard/
- **API Root**: http://localhost:8000/api/

