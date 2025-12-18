"""
RTSP Pipeline - Real-time CCTV monitoring with Django integration
Fetches active cameras from Django, processes RTSP streams, and sends alerts.
"""
import cv2
import time
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
from dotenv import load_dotenv
from ultralytics import YOLO

from threat_detector import ThreatDetector
from django_api import DjangoAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/rtsp_pipeline.log'),
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)

# Create logs directory
Path('logs').mkdir(exist_ok=True)

# Load configuration (only for pipeline-level settings, not detection configs)
load_dotenv()
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '3'))  # Seconds between camera polls
STREAM_TIMEOUT = int(os.getenv('STREAM_TIMEOUT', '10'))  # Stream connection timeout
RECONNECT_DELAY = int(os.getenv('RECONNECT_DELAY', '5'))  # Seconds before reconnecting
ALERT_COOLDOWN = int(os.getenv('ALERT_COOLDOWN', '5'))  # Seconds between alerts for same camera
MODEL_PATH = os.getenv('MODEL_PATH', 'yolov8n.pt')  # YOLO model path


class CameraStream:
    """Manages a single camera RTSP stream."""
    
    def __init__(self, camera_id: int, rtsp_url: str, model, 
                 threat_detector: ThreatDetector, django_client: DjangoAPIClient,
                 detection_config: Dict):
        """
        Initialize camera stream.
        
        Args:
            camera_id: Camera ID from Django
            rtsp_url: RTSP stream URL
            model: YOLO model instance
            threat_detector: ThreatDetector instance
            django_client: DjangoAPIClient instance
            detection_config: Detection config dict from backend
        """
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.model = model
        self.threat_detector = threat_detector
        self.django_client = django_client
        self.detection_config = detection_config
        self.cap = None
        self.frame_count = 0
        self.last_alert_time = 0
        self.frame_skip = detection_config.get('frame_skip', 30)
        self.confidence_threshold = detection_config.get('confidence_threshold', 0.6)
        
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
            # Skip frames for performance (using config from backend)
            self.frame_count += 1
            if self.frame_count % self.frame_skip != 0:
                # Still read to avoid buffer buildup
                self.cap.read()
                return None
            
            # Read frame
            ret, frame = self.cap.read()
            if not ret:
                logger.warning(f"Failed to read frame from camera {self.camera_id}")
                return None
            
            # Get current time for monitor mode check
            current_time = datetime.now()
            
            # Check if frame should be processed (using backend config)
            if not self.threat_detector.should_process_frame(current_time):
                return None  # Skip based on monitor mode
            
            # Run YOLO detection
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            
            # Parse detections
            detections = []
            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = self.model.names[cls_id]
                    
                    detections.append({
                        'class': class_name,
                        'class_id': cls_id,
                        'confidence': conf,
                        'bbox': box.xyxy[0].tolist(),
                    })
            
            if not detections:
                return None
            
            # Analyze for threats using backend rules
            detection_record = {
                'frame_number': self.frame_count,
                'timestamp': current_time,
                'detections': detections
            }
            
            threats = self.threat_detector.analyze_detections([detection_record])
            
            # Check for alert-worthy threats
            alert_threats = [t for t in threats if t['alert']]
            
            if alert_threats:
                # Cooldown check
                current_timestamp = time.time()
                if current_timestamp - self.last_alert_time < ALERT_COOLDOWN:
                    return None
                
                self.last_alert_time = current_timestamp
                
                # Get highest priority threat (HIGH > MEDIUM > LOW)
                priority_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
                highest_threat = max(alert_threats, 
                                   key=lambda x: (priority_order.get(x['threat_level'], 0), x['confidence']))
                
                # Map threat level to alert type
                alert_type_map = {
                    'HIGH': 'intrusion',
                    'MEDIUM': 'intrusion',
                    'LOW': 'suspicious'
                }
                alert_type = alert_type_map.get(highest_threat['threat_level'], 'suspicious')
                
                # Send alert to Django
                success = self.django_client.send_alert(
                    camera_id=self.camera_id,
                    alert_type=alert_type,
                    confidence=highest_threat['confidence'],
                    image_frame=frame,
                    description=f"{highest_threat['detected_class']} detected - {highest_threat['reason']}"
                )
                
                if success:
                    return {
                        'camera_id': self.camera_id,
                        'alert_type': alert_type,
                        'confidence': highest_threat['confidence'],
                        'threat_level': highest_threat['threat_level'],
                        'detected_class': highest_threat['detected_class'],
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing frame from camera {self.camera_id}: {e}")
            return None
    
    def is_connected(self) -> bool:
        """Check if stream is connected."""
        return self.cap is not None and self.cap.isOpened()


class RTSPPipeline:
    """Main RTSP pipeline orchestrator."""
    
    def __init__(self):
        """Initialize pipeline."""
        # Initialize Django API client
        self.django_client = DjangoAPIClient()
        
        # Load YOLO model (shared across cameras)
        logger.info(f"Loading YOLO model from {MODEL_PATH}")
        self.model = YOLO(MODEL_PATH)
        logger.info("YOLO model loaded successfully")
        
        # Camera streams with per-camera configs
        self.camera_streams: Dict[int, CameraStream] = {}
        
        logger.info("RTSP Pipeline initialized")
        logger.info(f"Django API: {self.django_client.api_url}")
        logger.info("Detection configs will be fetched from backend per camera")
    
    def update_camera_streams(self, cameras: list):
        """
        Update camera streams based on active cameras list.
        Each camera gets its own detection config from backend.
        
        Args:
            cameras: List of camera dictionaries from Django with effective_config
        """
        current_camera_ids = {cam['id'] for cam in cameras}
        stream_camera_ids = set(self.camera_streams.keys())
        
        # Remove disconnected cameras
        for camera_id in stream_camera_ids - current_camera_ids:
            logger.info(f"Removing camera {camera_id} (no longer active)")
            self.camera_streams[camera_id].disconnect()
            del self.camera_streams[camera_id]
        
        # Add new cameras or update existing ones with new configs
        for camera in cameras:
            camera_id = camera['id']
            detection_config = camera.get('effective_config', {})
            
            if camera_id not in self.camera_streams:
                # Create new stream with backend config
                logger.info(f"Adding camera {camera_id} with config: mode={detection_config.get('monitor_mode', 'unknown')}")
                
                # Create threat detector for this camera's config
                threat_detector = ThreatDetector(detection_config=detection_config)
                
                stream = CameraStream(
                    camera_id=camera_id,
                    rtsp_url=camera['rtsp_url'],
                    model=self.model,
                    threat_detector=threat_detector,
                    django_client=self.django_client,
                    detection_config=detection_config
                )
                if stream.connect():
                    self.camera_streams[camera_id] = stream
                else:
                    logger.warning(f"Failed to connect to camera {camera_id}")
            else:
                # Update existing stream's config if it changed
                existing_config = self.camera_streams[camera_id].detection_config
                if existing_config != detection_config:
                    logger.info(f"Updating config for camera {camera_id}")
                    self.camera_streams[camera_id].threat_detector.update_config(detection_config)
                    self.camera_streams[camera_id].detection_config = detection_config
                    self.camera_streams[camera_id].frame_skip = detection_config.get('frame_skip', 30)
                    self.camera_streams[camera_id].confidence_threshold = detection_config.get('confidence_threshold', 0.6)
        
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
                logger.info(f"Alert from camera {camera_id}: {alert_data['alert_type']} "
                          f"(confidence: {alert_data['confidence']:.2f})")
    
    def run(self):
        """Main pipeline loop."""
        logger.info("=" * 60)
        logger.info("RTSP Pipeline Starting")
        logger.info("=" * 60)
        
        try:
            while True:
                # Fetch active cameras from Django
                cameras = self.django_client.get_active_cameras()
                
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
    """Entry point for RTSP pipeline."""
    try:
        pipeline = RTSPPipeline()
        pipeline.run()
    except Exception as e:
        logger.error(f"Failed to start pipeline: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()

