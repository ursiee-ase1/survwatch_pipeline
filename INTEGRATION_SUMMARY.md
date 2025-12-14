# Django Integration Summary

## What Was Done

I've integrated Django into your existing pipeline and adapted the code to support RTSP streams. Here's what changed:

## New Files Created

### 1. `django_api.py`
- Django API client module
- Functions to fetch active cameras from Django
- Function to send alerts to Django
- Handles authentication with token
- Converts OpenCV frames to base64 for API

### 2. `rtsp_pipeline.py`
- Real-time RTSP stream processing pipeline
- Fetches cameras from Django API
- Connects to RTSP streams
- Uses your existing `AfterHoursDetector` and `ThreatDetector`
- Sends alerts to Django when threats detected
- Automatic reconnection on stream failure

### 3. `README_RTSP.md`
- Documentation for RTSP pipeline usage
- Setup instructions
- Configuration guide

## Modified Files

### 1. `detect_objects.py`
- **Added RTSP stream support**: Now accepts both video files and RTSP URLs
- Detects RTSP URLs by checking for `rtsp://` prefix
- Handles RTSP-specific properties (no frame count, etc.)
- Maintains backward compatibility with existing video file processing

### 2. `requirements.txt`
- Added `requests>=2.31.0` for Django API communication

## Existing Code Preserved

All your existing code remains unchanged and functional:
- ✅ `run_local_pipeline.py` - Still works for video file processing
- ✅ `detect_objects.py` - Now supports both files and RTSP
- ✅ `threat_detector.py` - Unchanged
- ✅ `extract_clips.py` - Unchanged
- ✅ All other existing modules - Unchanged

## How It Works

### RTSP Pipeline Flow

```
1. Pipeline starts → Fetches active cameras from Django
2. For each camera → Connects to RTSP stream
3. Processes frames → Uses AfterHoursDetector
4. Detects threats → Uses ThreatDetector
5. Sends alerts → Posts to Django API
6. Repeats → Polls Django every N seconds
```

### Integration Points

1. **Camera Management**: Django stores cameras, pipeline fetches them
2. **Alert Storage**: Pipeline sends alerts, Django stores them
3. **Authentication**: Token-based API authentication
4. **Real-time**: Continuous monitoring vs batch processing

## Usage

### For Video File Processing (Existing)
```bash
python run_local_pipeline.py
```
Works exactly as before - processes video files.

### For RTSP Stream Monitoring (New)
```bash
# 1. Setup Django (if not already done)
cd surveillance_backend
python manage.py runserver

# 2. Get API token
python create_token.py <username>

# 3. Add to .env
DJANGO_API_URL=http://localhost:8000
DJANGO_API_TOKEN=<your-token>

# 4. Run RTSP pipeline
python rtsp_pipeline.py
```

## Configuration

Add these to your `.env` file:

```env
# Django API
DJANGO_API_URL=http://localhost:8000
DJANGO_API_TOKEN=your-token-here

# RTSP Pipeline
FRAME_SKIP=30
POLL_INTERVAL=3
STREAM_TIMEOUT=10
RECONNECT_DELAY=5
ALERT_COOLDOWN=5

# Detection (already in your .env)
AFTER_HOURS_START=22
AFTER_HOURS_END=6
PERSON_CONFIDENCE=0.5
MODEL_PATH=yolov8n.pt
```

## Architecture

```
┌─────────────────┐
│  Django Backend │
│  (Port 8000)    │
└────────┬────────┘
         │
         │ HTTP API
         │
┌────────▼────────┐
│  RTSP Pipeline  │
│  (rtsp_pipeline)│
└────────┬────────┘
         │
         │ RTSP Streams
         │
┌────────▼────────┐
│  CCTV Cameras   │
└─────────────────┘
```

## Key Features

1. **Dual Mode**: Can process video files OR RTSP streams
2. **Django Integration**: Full API integration for cameras and alerts
3. **Existing Logic**: Uses your after-hours detection and threat classification
4. **Backward Compatible**: Existing video pipeline still works
5. **Real-time**: Continuous monitoring with automatic reconnection

## Next Steps

1. **Test Django Backend**: Ensure Django is running and accessible
2. **Add Cameras**: Use Django admin to add cameras with RTSP URLs
3. **Get API Token**: Create token using `create_token.py`
4. **Configure Pipeline**: Add Django settings to `.env`
5. **Run Pipeline**: Start `rtsp_pipeline.py` and monitor logs

## Troubleshooting

- **Can't connect to Django**: Check API URL and token
- **RTSP connection fails**: Verify RTSP URL format and credentials
- **No alerts**: Check after-hours time window and confidence threshold
- **Stream disconnects**: Pipeline will auto-reconnect

See `README_RTSP.md` for detailed troubleshooting.

