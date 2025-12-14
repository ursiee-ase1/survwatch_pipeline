# RTSP Pipeline with Django Integration

This document explains how to use the RTSP pipeline that integrates with the Django backend.

## Overview

The RTSP pipeline (`rtsp_pipeline.py`) is a real-time monitoring system that:
1. Fetches active cameras from Django API
2. Connects to RTSP streams
3. Processes frames with YOLOv8 detection
4. Sends alerts back to Django when threats are detected

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Add to your `.env` file:

```env
# Django API Configuration
DJANGO_API_URL=http://localhost:8000
DJANGO_API_TOKEN=your-api-token-here

# Pipeline Configuration
FRAME_SKIP=30              # Process every Nth frame
POLL_INTERVAL=3            # Seconds between camera polls
STREAM_TIMEOUT=10           # Stream connection timeout
RECONNECT_DELAY=5           # Seconds before reconnecting
ALERT_COOLDOWN=5            # Seconds between alerts for same camera

# Detection Configuration
AFTER_HOURS_START=22        # Hour when after-hours begins (24hr format)
AFTER_HOURS_END=6         # Hour when after-hours ends
PERSON_CONFIDENCE=0.5     # Detection confidence threshold
MODEL_PATH=yolov8n.pt     # Path to YOLOv8 model
```

### 3. Get API Token from Django

```bash
cd surveillance_backend
python create_token.py <your-username>
# Copy the token and add to .env
```

### 4. Run the Pipeline

```bash
python rtsp_pipeline.py
```

## How It Works

1. **Camera Fetching**: Every `POLL_INTERVAL` seconds, the pipeline fetches active cameras from Django
2. **Stream Connection**: Connects to each camera's RTSP URL
3. **Frame Processing**: Processes frames at the specified rate (every `FRAME_SKIP` frames)
4. **Threat Detection**: Uses your existing `AfterHoursDetector` and `ThreatDetector` classes
5. **Alert Sending**: Sends alerts to Django when HIGH or MEDIUM threats are detected

## Integration with Existing Code

The RTSP pipeline uses your existing detection code:
- `detect_objects.py` - Now supports RTSP streams (in addition to video files)
- `threat_detector.py` - Unchanged, used for threat classification
- `run_local_pipeline.py` - Still works for video file processing

## Differences from Video Pipeline

| Feature | Video Pipeline (`run_local_pipeline.py`) | RTSP Pipeline (`rtsp_pipeline.py`) |
|---------|------------------------------------------|-------------------------------------|
| Input | Video files | RTSP streams |
| Source | Local files | Django API |
| Processing | Batch (entire video) | Continuous (real-time) |
| Alerts | Saves to files | Sends to Django |
| After-hours | Filters by video timestamp | Filters by current time |

## Running Both Pipelines

You can run both pipelines simultaneously:
- **Video Pipeline**: For processing recorded video files
- **RTSP Pipeline**: For real-time monitoring of live streams

They use the same detection models and threat classification logic.

## Troubleshooting

### Pipeline can't connect to Django
- Check `DJANGO_API_URL` is correct
- Verify `DJANGO_API_TOKEN` is valid
- Ensure Django server is running

### RTSP stream connection fails
- Verify RTSP URL format: `rtsp://username:password@ip:port/path`
- Test stream with VLC player
- Check network connectivity
- Verify camera credentials

### No alerts being generated
- Check camera is marked as active in Django
- Verify after-hours time window
- Lower confidence threshold if needed
- Check pipeline logs for errors

