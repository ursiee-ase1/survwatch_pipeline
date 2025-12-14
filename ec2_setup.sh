#!/bin/bash
set -e

echo "=== CCTV Analysis EC2 Setup Script ==="
echo "Started at: $(date)"

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    git \
    wget \
    unzip

# Install AWS CLI
echo "Installing AWS CLI..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Upgrade pip
echo "Upgrading pip..."
python3 -m pip install --upgrade pip

# Install Python packages
echo "Installing Python packages..."
pip3 install --no-cache-dir \
    ultralytics \
    opencv-python-headless \
    boto3 \
    python-dotenv \
    numpy \
    Pillow \
    torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Create project directory
echo "Creating project directory..."
mkdir -p /home/ubuntu/cctv-analysis
cd /home/ubuntu/cctv-analysis

# Verify GPU
echo "Verifying GPU..."
nvidia-smi

# Test CUDA with PyTorch
echo "Testing CUDA with PyTorch..."
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}')"

# Download YOLOv8 model
echo "Downloading YOLOv8 model..."
python3 -c "from ultralytics import YOLO; model = YOLO('yolov8n.pt')"

# Create tmp directory for processing
mkdir -p /tmp/cctv-processing

echo "=== Setup Complete ==="
echo "Finished at: $(date)"