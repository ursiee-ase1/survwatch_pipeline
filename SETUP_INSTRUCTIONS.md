# Setup Instructions

## Overview

The Django backend should be created as a **separate project** from `cctv-analysis`.

- **cctv-analysis**: Contains the AI pipeline code (detection, RTSP processing)
- **surveillance-backend**: Separate Django project (user management, API, dashboard)

## Step 1: Create Django Project (Separate Location)

### Option A: Use Generator Script

1. Create a new directory for Django:
   ```powershell
   cd C:\
   mkdir surveillance-backend
   cd surveillance-backend
   ```

2. Copy and run the generator:
   ```powershell
   # From cctv-analysis directory, copy the generator
   python C:\cctv-analysis\generate_django_project.py C:\surveillance-backend
   ```

### Option B: Manual Setup

1. Create directory:
   ```powershell
   cd C:\
   mkdir surveillance-backend
   cd surveillance-backend
   ```

2. Create virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. Install Django:
   ```powershell
   pip install Django>=4.2.0 djangorestframework django-cors-headers Pillow python-dotenv
   ```

4. Create Django project:
   ```powershell
   django-admin startproject surveillance_backend .
   python manage.py startapp surveillance
   ```

5. Copy files from `cctv-analysis/surveillance_backend/` to your new project

## Step 2: Setup Django Project

```powershell
cd C:\surveillance-backend

# Activate venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Get API token
python create_token.py <your-username>
# Copy the token!
```

## Step 3: Configure cctv-analysis

In your `cctv-analysis` project, add to `.env`:

```env
DJANGO_API_URL=http://localhost:8000
DJANGO_API_TOKEN=<paste-token-from-step-2>
```

## Step 4: Test Connection

From `cctv-analysis`:

```powershell
python -c "from django_api import DjangoAPIClient; c = DjangoAPIClient(); print(f'Cameras: {len(c.get_active_cameras())}')"
```

## Project Structure

```
C:\
├── cctv-analysis\              # Your existing pipeline project
│   ├── django_api.py          # API client (stays here)
│   ├── rtsp_pipeline.py       # RTSP pipeline (stays here)
│   ├── detect_objects.py       # Detection code
│   └── .env                    # Contains DJANGO_API_URL and token
│
└── surveillance-backend\       # NEW separate Django project
    ├── venv\                   # Virtual environment
    ├── manage.py
    ├── surveillance_backend\   # Django settings
    ├── surveillance\          # Django app
    └── .env                    # Django settings
```

## Running Both Projects

### Terminal 1: Django Backend
```powershell
cd C:\surveillance-backend
.\venv\Scripts\Activate.ps1
python manage.py runserver
```

### Terminal 2: RTSP Pipeline
```powershell
cd C:\cctv-analysis
conda activate cctv
python rtsp_pipeline.py
```

## Important Notes

- Django project is **completely separate** from cctv-analysis
- They communicate via HTTP API only
- No shared code or dependencies
- Django can be on a different server in production

