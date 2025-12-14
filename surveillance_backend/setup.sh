#!/bin/bash
# Setup script for Django surveillance backend

echo "Setting up Django Surveillance Backend..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
DJANGO_SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EOF
    echo ".env file created with random SECRET_KEY"
fi

# Create logs directory
mkdir -p logs

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Create superuser prompt
echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Create a superuser: python manage.py createsuperuser"
echo "2. Create an API token:"
echo "   python manage.py shell"
echo "   >>> from django.contrib.auth.models import User"
echo "   >>> from rest_framework.authtoken.models import Token"
echo "   >>> user = User.objects.first()"
echo "   >>> token = Token.objects.create(user=user)"
echo "   >>> print(token.key)"
echo ""
echo "3. Run the server: python manage.py runserver"
echo ""

