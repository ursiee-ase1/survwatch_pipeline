"""
Configuration module for CCTV pipeline.
Loads settings from environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Django API Configuration
DJANGO_API_URL = os.getenv('DJANGO_API_URL', 'http://localhost:8000')
DJANGO_API_TOKEN = os.getenv('DJANGO_API_TOKEN', '')

# Model Configuration
MODEL_PATH = os.getenv('MODEL_PATH', 'yolov8n.pt')
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.5'))

# Detection Configuration
ALERT_TYPES = {
    'person': 'person',
    'fire': 'fire',
    'smoke': 'smoke',
    'violence': 'violence',
    'intrusion': 'intrusion',
    'suspicious': 'suspicious',
}

# Pipeline Configuration
FRAME_SKIP = int(os.getenv('FRAME_SKIP', '30'))  # Process every Nth frame
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '3'))  # Seconds between camera polls
STREAM_TIMEOUT = int(os.getenv('STREAM_TIMEOUT', '10'))  # Seconds to wait for stream
RECONNECT_DELAY = int(os.getenv('RECONNECT_DELAY', '5'))  # Seconds before reconnecting

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/pipeline.log')

# Create logs directory if it doesn't exist
Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

