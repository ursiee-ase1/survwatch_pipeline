# System Architecture

## Overview

The CCTV Analytics Platform consists of two main components:

1. **Django Backend** - Web application and REST API
2. **AI Pipeline** - Standalone detection service

## Component Details

### Django Backend (`surveillance_backend/`)

**Purpose**: User management, camera registration, alert storage, API endpoints

**Technology Stack**:
- Django 4.2+
- Django REST Framework
- SQLite (development) / PostgreSQL (production)
- Token Authentication

**Key Components**:
- `surveillance/models.py` - Camera and Alert models
- `surveillance/views.py` - API views and dashboard
- `surveillance/serializers.py` - DRF serializers
- `surveillance/admin.py` - Django admin interface
- `templates/surveillance/dashboard.html` - Web dashboard

**API Endpoints**:
- `GET /api/cameras/` - List cameras
- `POST /api/cameras/` - Create camera
- `POST /api/cameras/<id>/activate/` - Activate camera
- `POST /api/cameras/<id>/deactivate/` - Deactivate camera
- `GET /api/active-cameras/` - Get active cameras (for pipeline)
- `POST /api/send-alert/` - Send alert (from pipeline)
- `GET /api/alerts/` - List alerts
- `GET /dashboard/` - Web dashboard

### AI Pipeline (`cctv/`)

**Purpose**: Real-time threat detection from RTSP streams

**Technology Stack**:
- Python 3.10+
- YOLOv8 (Ultralytics)
- OpenCV
- Conda environment

**Key Components**:
- `pipeline.py` - Main orchestration loop
- `detectors/model.py` - YOLOv8 threat detector
- `detectors/utils.py` - Image processing utilities
- `config.py` - Configuration loader

**Workflow**:
1. Poll Django API for active cameras
2. Connect to RTSP streams
3. Process frames with YOLOv8
4. Detect threats (intrusion, person, vehicle, etc.)
5. Send alerts back to Django API

## Data Flow

```
┌─────────────┐
│   Camera    │
│  RTSP Feed  │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Pipeline  │─────▶│ YOLOv8 Model │─────▶│   Detector   │
│             │      │              │      │             │
└──────┬──────┘      └──────────────┘      └──────┬──────┘
       │                                           │
       │                                           │
       │  GET /api/active-cameras/                 │ Alert Detected
       │◀─────────────────────────────────────────┘
       │
       │  POST /api/send-alert/
       ▼
┌─────────────┐
│   Django    │
│   Backend   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Database   │
│  (Alerts)   │
└─────────────┘
```

## Authentication Flow

1. User creates account in Django
2. Django generates API token via `Token.objects.create(user=user)`
3. Pipeline uses token in `Authorization: Token <token>` header
4. Django validates token on each API request

## Database Schema

### Camera Model
- `id` - Primary key
- `user` - Foreign key to User
- `name` - Camera name
- `rtsp_url` - RTSP stream URL
- `is_active` - Boolean flag
- `created_at` - Timestamp
- `updated_at` - Timestamp

### Alert Model
- `id` - Primary key
- `camera` - Foreign key to Camera
- `alert_type` - Choice field (violence, intrusion, fire, etc.)
- `confidence` - Float (0.0-1.0)
- `timestamp` - DateTime
- `image` - ImageField (optional)
- `description` - TextField
- `acknowledged` - Boolean flag

## Deployment Architecture

### Development
- Django: `python manage.py runserver` (port 8000)
- Pipeline: `python pipeline.py` (same machine)

### Production
- Django: Gunicorn + Nginx (port 80/443)
- Pipeline: Systemd service on separate server
- Database: PostgreSQL
- Storage: S3 or local filesystem for alert images

## Scalability Considerations

1. **Multiple Pipeline Instances**: Can run multiple pipeline processes for different camera groups
2. **Load Balancing**: Django can be load-balanced behind Nginx
3. **Database**: Use PostgreSQL with connection pooling
4. **Caching**: Add Redis for frequently accessed data
5. **Message Queue**: Use Celery + Redis for async alert processing
6. **CDN**: Serve alert images via CDN

## Security

- Token authentication for API
- HTTPS in production
- Secure RTSP streams
- Input validation on all endpoints
- SQL injection protection (Django ORM)
- XSS protection (Django templates)
- CSRF protection (Django middleware)

