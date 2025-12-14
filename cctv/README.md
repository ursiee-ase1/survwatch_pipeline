# CCTV AI Pipeline

Standalone AI pipeline for CCTV threat detection.

## Setup

```bash
# Create conda environment
conda env create -f environment.yml

# Activate environment
conda activate cctv

# Configure environment
cp .env.example .env
# Edit .env with your Django API URL and token

# Run pipeline
python pipeline.py
```

## Configuration

Edit `.env` file:

- `DJANGO_API_URL`: Django backend URL
- `DJANGO_API_TOKEN`: API authentication token
- `MODEL_PATH`: Path to YOLOv8 model file
- `CONFIDENCE_THRESHOLD`: Detection confidence (0.0-1.0)
- `FRAME_SKIP`: Process every Nth frame
- `POLL_INTERVAL`: Seconds between camera polls

## Requirements

- Conda environment with Python 3.10+
- YOLOv8 model file (auto-downloads on first run)
- Access to RTSP camera streams
- Django backend running and accessible

