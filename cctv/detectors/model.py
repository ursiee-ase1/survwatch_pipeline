"""
AI Detection Model Module
Uses YOLOv8 for object detection and threat classification.
"""
import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ThreatDetector:
    """
    Threat detection using YOLOv8 model.
    Detects various threats: violence, intrusion, fire, smoke, persons, etc.
    """
    
    # COCO class IDs for threat detection
    PERSON_CLASS = 0
    FIRE_CLASS = None  # Not in COCO, will use custom logic
    SMOKE_CLASS = None  # Not in COCO, will use custom logic
    
    # Threat categories
    THREAT_CLASSES = {
        'person': ['person'],
        'vehicle': ['car', 'truck', 'bus', 'motorcycle'],
        'violence': ['person'],  # Can be extended with violence detection model
        'intrusion': ['person', 'car', 'truck'],
        'fire': [],  # Requires specialized model
        'smoke': [],  # Requires specialized model
    }
    
    def __init__(self, model_path='yolov8n.pt', confidence_threshold=0.5):
        """
        Initialize the threat detector.
        
        Args:
            model_path: Path to YOLOv8 model file
            confidence_threshold: Minimum confidence for detections
        """
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the YOLOv8 model."""
        try:
            logger.info(f"Loading YOLOv8 model from {self.model_path}")
            self.model = YOLO(str(self.model_path))
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def predict(self, frame):
        """
        Run detection on a frame.
        
        Args:
            frame: OpenCV frame (numpy array)
            
        Returns:
            dict: Detection results with alert information
            {
                'alert': bool,
                'type': str,
                'confidence': float,
                'detections': list,
            }
        """
        if self.model is None:
            logger.error("Model not loaded")
            return {
                'alert': False,
                'type': None,
                'confidence': 0.0,
                'detections': [],
            }
        
        try:
            # Run YOLOv8 detection
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            
            # Parse results
            detections = []
            alert_detected = False
            alert_type = None
            max_confidence = 0.0
            
            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = self.model.names[cls_id]
                    
                    detection = {
                        'class': class_name,
                        'class_id': cls_id,
                        'confidence': conf,
                        'bbox': box.xyxy[0].tolist(),
                    }
                    detections.append(detection)
                    
                    # Check for threats
                    threat_type = self._classify_threat(class_name, conf)
                    if threat_type:
                        alert_detected = True
                        if conf > max_confidence:
                            max_confidence = conf
                            alert_type = threat_type
            
            # Determine alert type based on detections
            if alert_detected:
                alert_type = self._determine_alert_type(detections)
            
            return {
                'alert': alert_detected,
                'type': alert_type,
                'confidence': max_confidence if alert_detected else 0.0,
                'detections': detections,
            }
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return {
                'alert': False,
                'type': None,
                'confidence': 0.0,
                'detections': [],
            }
    
    def _classify_threat(self, class_name, confidence):
        """
        Classify if a detected object is a threat.
        
        Args:
            class_name: Detected object class name
            confidence: Detection confidence
            
        Returns:
            str or None: Threat type if threat detected, None otherwise
        """
        class_name_lower = class_name.lower()
        
        # Person detection (intrusion after hours)
        if class_name_lower == 'person':
            return 'intrusion'
        
        # Vehicle detection (intrusion)
        if class_name_lower in ['car', 'truck', 'bus', 'motorcycle']:
            return 'intrusion'
        
        # Note: Fire and smoke detection would require specialized models
        # Violence detection would require action recognition models
        
        return None
    
    def _determine_alert_type(self, detections):
        """
        Determine the primary alert type from multiple detections.
        
        Args:
            detections: List of detection dictionaries
            
        Returns:
            str: Primary alert type
        """
        if not detections:
            return None
        
        # Count detections by type
        person_count = sum(1 for d in detections if d['class'].lower() == 'person')
        vehicle_count = sum(1 for d in detections 
                           if d['class'].lower() in ['car', 'truck', 'bus', 'motorcycle'])
        
        # Prioritize person detection
        if person_count > 0:
            return 'intrusion'
        elif vehicle_count > 0:
            return 'intrusion'
        else:
            return 'suspicious'

