#!/bin/bash
# TaawaVault Setup Script

echo "Setting up TaawaVault..."

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
    cp .env.example .env
    echo "Please edit .env file with your configuration"
fi

# Create necessary directories
mkdir -p logs
mkdir -p media
mkdir -p staticfiles

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Create superuser
echo "Creating superuser..."
python manage.py createsuperuser

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Setup complete!"
echo "To start the development server, run: python manage.py runserver"
echo "To start Celery worker, run: celery -A config worker -l info"
