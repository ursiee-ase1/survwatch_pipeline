#!/bin/bash
# Create example .env files

# Django .env.example
cat > surveillance_backend/.env.example << 'EOF'
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EOF

# Pipeline .env.example
cat > cctv/.env.example << 'EOF'
# Django API Configuration
DJANGO_API_URL=http://localhost:8000
DJANGO_API_TOKEN=your-api-token-here

# Model Configuration
MODEL_PATH=yolov8n.pt
CONFIDENCE_THRESHOLD=0.5

# Pipeline Configuration
FRAME_SKIP=30
POLL_INTERVAL=3
STREAM_TIMEOUT=10
RECONNECT_DELAY=5

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/pipeline.log
EOF

echo "Example .env files created!"

