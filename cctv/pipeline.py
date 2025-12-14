"""
Main CCTV Pipeline Script
Fetches active cameras from Django, processes RTSP streams, and sends alerts.
"""
import cv2
import time
import logging
import requests
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cctv.config import (
    DJANGO_API_URL,
    DJANGO_API_TOKEN,
    MODEL_PATH,
    CONFIDENCE_THRESHOLD,
    FRAME_SKIP,
    POLL_INTERVAL,
    STREAM_TIMEOUT,
    RECONNECT_DELAY,
    LOG_LEVEL,
    LOG_FILE,
)
from cctv.detectors.model import ThreatDetector
from cctv.detectors.utils import frame_to_base64

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


class CameraStream:
    """Manages a single camera RTSP stream."""
    
    def __init__(self, camera_id: int, rtsp_url: str, detector: ThreatDetector):
        """
        Initialize camera stream.
        
        Args:
            camera_id: Camera ID from Django
            rtsp_url: RTSP stream URL
            detector: ThreatDetector instance
        """
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.detector = detector
        self.cap = None
        self.frame_count = 0
        self.last_alert_time = 0
        self.alert_cooldown = 5  # Seconds between alerts for same camera
        
    def connect(self) -> bool:
        """
        Connect to RTSP stream.
        
        Returns:
            bool: True if connection successful
        """
        try:
            logger.info(f"Connecting to camera {self.camera_id}: {self.rtsp_url}")
            self.cap = cv2.VideoCapture(self.rtsp_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
            
            # Test connection
            ret, frame = self.cap.read()
            if ret:
                logger.info(f"✓ Connected to camera {self.camera_id}")
                return True
            else:
                logger.warning(f"✗ Failed to read frame from camera {self.camera_id}")
                self.disconnect()
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to camera {self.camera_id}: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Disconnect from stream."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            logger.info(f"Disconnected from camera {self.camera_id}")
    
    def process_frame(self) -> Optional[Dict]:
        """
        Process a frame from the stream.
        
        Returns:
            dict or None: Alert data if threat detected, None otherwise
        """
        if self.cap is None or not self.cap.isOpened():
            return None
        
        try:
            # Skip frames for performance
            self.frame_count += 1
            if self.frame_count % FRAME_SKIP != 0:
                # Still read to avoid buffer buildup
                self.cap.read()
                return None
            
            # Read frame
            ret, frame = self.cap.read()
            if not ret:
                logger.warning(f"Failed to read frame from camera {self.camera_id}")
                return None
            
            # Run detection
            result = self.detector.predict(frame)
            
            # Check for alerts
            if result['alert']:
                # Cooldown check
                current_time = time.time()
                if current_time - self.last_alert_time < self.alert_cooldown:
                    return None
                
                self.last_alert_time = current_time
                
                # Convert frame to base64
                image_base64 = frame_to_base64(frame)
                
                return {
                    'camera_id': self.camera_id,
                    'alert_type': result['type'],
                    'confidence': result['confidence'],
                    'image_base64': image_base64,
                    'detections': result['detections'],
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing frame from camera {self.camera_id}: {e}")
            return None
    
    def is_connected(self) -> bool:
        """Check if stream is connected."""
        return self.cap is not None and self.cap.isOpened()


class Pipeline:
    """Main pipeline orchestrator."""
    
    def __init__(self):
        """Initialize pipeline."""
        self.detector = None
        self.camera_streams: Dict[int, CameraStream] = {}
        self.api_url = DJANGO_API_URL.rstrip('/')
        self.api_token = DJANGO_API_TOKEN
        
        # Validate configuration
        if not self.api_token:
            logger.warning("DJANGO_API_TOKEN not set - API calls may fail")
        
        self._load_detector()
    
    def _load_detector(self):
        """Load the threat detection model."""
        try:
            logger.info("Loading threat detection model...")
            self.detector = ThreatDetector(
                model_path=MODEL_PATH,
                confidence_threshold=CONFIDENCE_THRESHOLD
            )
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load detector: {e}")
            raise
    
    def get_active_cameras(self) -> List[Dict]:
        """
        Fetch active cameras from Django API.
        
        Returns:
            List of camera dictionaries with 'id' and 'rtsp_url'
        """
        try:
            url = f"{self.api_url}/api/active-cameras/"
            headers = {
                'Authorization': f'Token {self.api_token}',
                'Content-Type': 'application/json',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            cameras = response.json()
            logger.info(f"Fetched {len(cameras)} active cameras")
            return cameras
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch cameras: {e}")
            return []
    
    def post_alert(self, alert_data: Dict) -> bool:
        """
        Send alert to Django API.
        
        Args:
            alert_data: Alert dictionary with camera_id, alert_type, confidence, image_base64
            
        Returns:
            bool: True if alert sent successfully
        """
        try:
            url = f"{self.api_url}/api/send-alert/"
            headers = {
                'Authorization': f'Token {self.api_token}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'camera_id': alert_data['camera_id'],
                'alert_type': alert_data['alert_type'],
                'confidence': alert_data['confidence'],
                'image_base64': alert_data.get('image_base64', ''),
                'description': f"Detected {len(alert_data.get('detections', []))} objects",
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            logger.info(f"✓ Alert sent for camera {alert_data['camera_id']}: {alert_data['alert_type']}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send alert: {e}")
            return False
    
    def update_camera_streams(self, cameras: List[Dict]):
        """
        Update camera streams based on active cameras list.
        
        Args:
            cameras: List of camera dictionaries
        """
        current_camera_ids = {cam['id'] for cam in cameras}
        stream_camera_ids = set(self.camera_streams.keys())
        
        # Remove disconnected cameras
        for camera_id in stream_camera_ids - current_camera_ids:
            logger.info(f"Removing camera {camera_id} (no longer active)")
            self.camera_streams[camera_id].disconnect()
            del self.camera_streams[camera_id]
        
        # Add new cameras
        for camera in cameras:
            camera_id = camera['id']
            if camera_id not in self.camera_streams:
                logger.info(f"Adding camera {camera_id}")
                stream = CameraStream(
                    camera_id=camera_id,
                    rtsp_url=camera['rtsp_url'],
                    detector=self.detector
                )
                if stream.connect():
                    self.camera_streams[camera_id] = stream
                else:
                    logger.warning(f"Failed to connect to camera {camera_id}")
        
        # Reconnect disconnected streams
        for camera_id, stream in self.camera_streams.items():
            if not stream.is_connected():
                logger.info(f"Reconnecting camera {camera_id}")
                stream.connect()
    
    def process_streams(self):
        """Process all active camera streams."""
        for camera_id, stream in list(self.camera_streams.items()):
            if not stream.is_connected():
                continue
            
            alert_data = stream.process_frame()
            if alert_data:
                self.post_alert(alert_data)
    
    def run(self):
        """Main pipeline loop."""
        logger.info("=" * 60)
        logger.info("CCTV Pipeline Starting")
        logger.info("=" * 60)
        logger.info(f"API URL: {self.api_url}")
        logger.info(f"Model: {MODEL_PATH}")
        logger.info(f"Confidence Threshold: {CONFIDENCE_THRESHOLD}")
        logger.info(f"Frame Skip: {FRAME_SKIP}")
        logger.info("=" * 60)
        
        try:
            while True:
                # Fetch active cameras
                cameras = self.get_active_cameras()
                
                # Update streams
                if cameras:
                    self.update_camera_streams(cameras)
                
                # Process streams
                if self.camera_streams:
                    self.process_streams()
                else:
                    logger.debug("No active cameras to process")
                
                # Sleep before next poll
                time.sleep(POLL_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("Pipeline stopped by user")
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
        finally:
            # Cleanup
            logger.info("Cleaning up streams...")
            for stream in self.camera_streams.values():
                stream.disconnect()
            logger.info("Pipeline shutdown complete")


def main():
    """Entry point for pipeline."""
    try:
        pipeline = Pipeline()
        pipeline.run()
    except Exception as e:
        logger.error(f"Failed to start pipeline: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

