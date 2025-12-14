# Quick Start Guide

## 5-Minute Setup

### Step 1: Django Backend (2 minutes)

```bash
cd surveillance_backend

# Install dependencies
pip install -r requirements.txt

# Setup (creates .env, runs migrations)
python manage.py migrate

# Create superuser
python manage.py createsuperuser
# Enter username, email, password

# Create API token
python create_token.py <your-username>
# Copy the token shown

# Run server
python manage.py runserver
```

Backend is now running at `http://localhost:8000`

### Step 2: Pipeline (3 minutes)

```bash
cd cctv

# Create conda environment
conda env create -f environment.yml

# Activate
conda activate cctv

# Create .env file
cat > .env << EOF
DJANGO_API_URL=http://localhost:8000
DJANGO_API_TOKEN=<paste-token-from-step-1>
MODEL_PATH=yolov8n.pt
CONFIDENCE_THRESHOLD=0.5
FRAME_SKIP=30
POLL_INTERVAL=3
LOG_LEVEL=INFO
LOG_FILE=logs/pipeline.log
EOF

# Run pipeline
python pipeline.py
```

### Step 3: Add a Camera

1. Go to `http://localhost:8000/admin`
2. Login with superuser credentials
3. Navigate to **Surveillance > Cameras**
4. Click **Add Camera**
5. Fill in:
   - User: Your username
   - Name: "Test Camera"
   - RTSP URL: `rtsp://your-camera-url`
   - Is active: ✓ (checked)

The pipeline will automatically detect and start monitoring the camera!

## Testing Without Real Camera

You can test with a test RTSP stream:

```bash
# Install test RTSP server (optional)
# Or use a public test stream:
# rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4
```

## Verify Everything Works

1. **Django Admin**: http://localhost:8000/admin
2. **Dashboard**: http://localhost:8000/dashboard/
3. **API**: http://localhost:8000/api/cameras/
4. **Pipeline logs**: Check `cctv/logs/pipeline.log`

## Common Issues

**Pipeline can't connect to Django:**
- Check Django is running
- Verify API token in `cctv/.env`
- Check `DJANGO_API_URL` is correct

**No cameras found:**
- Ensure camera is marked as "active" in Django admin
- Check camera RTSP URL is correct

**Model not loading:**
- Model downloads automatically on first run
- Check internet connection
- Verify `MODEL_PATH` in `.env`

