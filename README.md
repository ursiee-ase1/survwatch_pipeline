# CCTV Analytics Platform

A complete cloud-based CCTV analytics platform with Django backend and standalone AI pipeline for real-time threat detection.

## 🎯 Features

- **Django SaaS Backend**: User accounts, camera management, alert storage
- **REST API**: Full API for camera and alert management
- **AI Detection Pipeline**: Standalone pipeline using YOLOv8 for threat detection
- **Real-time Monitoring**: RTSP stream processing with automatic reconnection
- **Alert System**: Automatic alert generation and storage
- **Dashboard**: Web-based dashboard for monitoring cameras and alerts
- **Admin Panel**: Django admin interface for management

## 📋 System Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  Django Backend │◄────────┤  AI Pipeline     │
│  (Port 8000)    │  HTTP   │  (Conda env)     │
└─────────────────┘         └──────────────────┘
         │                           │
         │                           │
    ┌────▼────┐                ┌────▼────┐
    │  Users  │                │  RTSP   │
    │  Admin  │                │ Streams │
    └─────────┘                └─────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Conda (for pipeline environment)
- Django 4.2+
- Access to RTSP camera streams

### 1. Backend Setup

The pipeline connects to a Django backend service via HTTP API. Ensure your backend is running and accessible. The backend should provide these endpoints:

- `GET /api/active-cameras/` - Returns active cameras with detection configs
- `POST /api/send-alert/` - Accepts alerts from the pipeline

**Note:** The backend is a separate service (not included in this repository). Configure the backend URL in the pipeline `.env` file.

### 2. Pipeline Setup (Conda Environment)

```bash
# Navigate to pipeline directory
cd cctv

# Create conda environment
conda env create -f environment.yml

# Activate environment
conda activate cctv

# Copy environment file
cp .env.example .env

# Edit .env and set:
# - DJANGO_API_URL (e.g., http://localhost:8000)
# - DJANGO_API_TOKEN (from Django setup above)
# - MODEL_PATH (default: yolov8n.pt)
# - CONFIDENCE_THRESHOLD (default: 0.5)

# Download YOLOv8 model (if not present)
# The model will auto-download on first run, or download manually:
# wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

### 3. Running the Pipeline

```bash
# Activate conda environment
conda activate cctv

# Run pipeline
python pipeline.py
```

The pipeline will:
1. Fetch active cameras from Django API
2. Connect to RTSP streams
3. Process frames with YOLOv8
4. Send alerts back to Django when threats are detected

## 📁 Project Structure

```
.
├── cctv/                           # Standalone pipeline
│   ├── pipeline.py                 # Main pipeline script
│   ├── config.py                   # Configuration loader
│   ├── detectors/
│   │   ├── model.py              # YOLOv8 detector
│   │   └── utils.py               # Utility functions
│   ├── environment.yml             # Conda environment
│   └── .env                        # Pipeline config
│
├── rtsp_pipeline.py                # RTSP stream processing pipeline
├── threat_detector.py              # Backend-driven threat detection
├── django_api.py                   # HTTP client for backend API
├── detect_objects.py               # Object detection utilities
├── requirements.txt                # Python dependencies
└── README.md
```

**Note:** This repository contains only the **pipeline code**. The Django backend is a separate service that runs independently and communicates with the pipeline via HTTP API.

## 🔌 API Endpoints

### Authentication

All API endpoints require authentication using Token Authentication.

**Get Token:**
```bash
curl -X POST http://localhost:8000/api-token-auth/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

### Camera Endpoints

**List Cameras:**
```bash
GET /api/cameras/
Authorization: Token <your-token>
```

**Create Camera:**
```bash
POST /api/cameras/
Authorization: Token <your-token>
Content-Type: application/json

{
  "name": "Front Door Camera",
  "rtsp_url": "rtsp://username:password@camera-ip:554/stream"
}
```

**Activate Camera:**
```bash
POST /api/cameras/<id>/activate/
Authorization: Token <your-token>
```

**Deactivate Camera:**
```bash
POST /api/cameras/<id>/deactivate/
Authorization: Token <your-token>
```

**Get Active Cameras (for pipeline):**
```bash
GET /api/active-cameras/
Authorization: Token <your-token>

Response:
[
  {"id": 1, "rtsp_url": "rtsp://..."},
  {"id": 2, "rtsp_url": "rtsp://..."}
]
```

### Alert Endpoints

**Send Alert (used by pipeline):**
```bash
POST /api/send-alert/
Authorization: Token <your-token>
Content-Type: application/json

{
  "camera_id": 1,
  "alert_type": "intrusion",
  "confidence": 0.85,
  "image_base64": "base64-encoded-image-string",
  "description": "Person detected"
}
```

**List Alerts:**
```bash
GET /api/alerts/
Authorization: Token <your-token>
```

**Acknowledge Alert:**
```bash
POST /api/alerts/<id>/acknowledge/
Authorization: Token <your-token>
```

## 🎥 Adding Cameras

### Via Django Admin

1. Go to `http://localhost:8000/admin`
2. Login with superuser credentials
3. Navigate to **Surveillance > Cameras**
4. Click **Add Camera**
5. Fill in:
   - **User**: Select your user
   - **Name**: Camera identifier
   - **RTSP URL**: Full RTSP stream URL
   - **Is active**: Check to enable monitoring

### Via API

```bash
curl -X POST http://localhost:8000/api/cameras/ \
  -H "Authorization: Token <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Parking Lot Camera",
    "rtsp_url": "rtsp://admin:password@192.168.1.100:554/stream1"
  }'
```

### RTSP URL Format

```
rtsp://username:password@ip-address:port/path
```

Examples:
- `rtsp://admin:password123@192.168.1.100:554/stream1`
- `rtsp://user:pass@camera.example.com:8554/live`
- `rtsp://192.168.1.50:554/onvif1` (if no auth)

## 🔍 Detection Types

The pipeline detects the following alert types:

- **intrusion**: Person or vehicle detected
- **person**: Person detected
- **vehicle**: Vehicle detected
- **suspicious**: Other suspicious activity
- **violence**: Violence detection (requires specialized model)
- **fire**: Fire detection (requires specialized model)
- **smoke**: Smoke detection (requires specialized model)

## ⚙️ Configuration

### Pipeline Settings

Edit `cctv/.env`:

```env
DJANGO_API_URL=http://localhost:8000
DJANGO_API_TOKEN=your-api-token

MODEL_PATH=yolov8n.pt
CONFIDENCE_THRESHOLD=0.5

FRAME_SKIP=30          # Process every Nth frame
POLL_INTERVAL=3        # Seconds between camera polls
STREAM_TIMEOUT=10      # Stream connection timeout
RECONNECT_DELAY=5      # Seconds before reconnecting

LOG_LEVEL=INFO
LOG_FILE=logs/pipeline.log
```

## 📊 Dashboard

Access the dashboard at: `http://localhost:8000/dashboard/`

Features:
- View all cameras and their status
- See recent alerts with images
- Activate/deactivate cameras
- View alert statistics

## 🛠️ Development

### Running Tests

```bash
# Pipeline tests (manual)
cd cctv
python -c "from detectors.model import ThreatDetector; print('OK')"
```

### Logging

- **Pipeline logs**: `cctv/logs/pipeline.log` or `logs/rtsp_pipeline.log`

### Database

Default: SQLite (`db.sqlite3`)

For production, use PostgreSQL:

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'surveillance_db',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 🚀 Production Deployment

### Pipeline

1. Create systemd service:

```ini
[Unit]
Description=CCTV Pipeline
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/cctv
Environment="PATH=/path/to/conda/envs/cctv/bin"
ExecStart=/path/to/conda/envs/cctv/bin/python pipeline.py
Restart=always

[Install]
WantedBy=multi-user.target
```

2. Enable and start:
```bash
sudo systemctl enable cctv-pipeline
sudo systemctl start cctv-pipeline
```

## 🔒 Security Notes

- **Never commit `.env` files** to version control
- Use strong `SECRET_KEY` in production
- Use HTTPS in production
- Secure RTSP streams with authentication
- Rotate API tokens regularly
- Limit API access with firewall rules

## 📝 Troubleshooting

### Pipeline can't connect to Django

- Check `DJANGO_API_URL` is correct
- Verify `DJANGO_API_TOKEN` is valid
- Ensure Django server is running
- Check firewall/network settings

### RTSP stream connection fails

- Verify RTSP URL format
- Check camera credentials
- Test stream with VLC player
- Ensure network connectivity
- Check camera supports RTSP

### No alerts being generated

- Verify camera is marked as active
- Check confidence threshold (lower = more alerts)
- Ensure model file exists
- Check pipeline logs for errors

### Model not loading

- Download YOLOv8 model: `yolov8n.pt`
- Check `MODEL_PATH` in `.env`
- Verify file permissions

## 📚 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [OpenCV RTSP Guide](https://docs.opencv.org/)

## 📄 License

This project is provided as-is for educational and development purposes.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Built with ❤️ for CCTV Analytics**

