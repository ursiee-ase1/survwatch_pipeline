"""
Utility functions for detection pipeline.
"""
import cv2
import base64
import numpy as np
from io import BytesIO
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def frame_to_base64(frame, quality=85):
    """
    Convert OpenCV frame to base64-encoded JPEG string.
    
    Args:
        frame: OpenCV frame (numpy array)
        quality: JPEG quality (1-100)
        
    Returns:
        str: Base64-encoded image string
    """
    try:
        # Encode frame as JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        success, buffer = cv2.imencode('.jpg', frame, encode_param)
        
        if not success:
            logger.error("Failed to encode frame")
            return None
        
        # Convert to base64
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        return image_base64
        
    except Exception as e:
        logger.error(f"Error converting frame to base64: {e}")
        return None


def annotate_frame(frame, detections, model_names=None):
    """
    Annotate frame with detection boxes and labels.
    
    Args:
        frame: OpenCV frame
        detections: List of detection dictionaries
        model_names: Optional class name mapping
        
    Returns:
        Annotated frame
    """
    annotated = frame.copy()
    
    for det in detections:
        bbox = det['bbox']
        class_name = det['class']
        confidence = det['confidence']
        
        # Draw bounding box
        x1, y1, x2, y2 = map(int, bbox)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Draw label
        label = f"{class_name} {confidence:.2f}"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(annotated, (x1, y1 - label_size[1] - 10), 
                     (x1 + label_size[0], y1), (0, 255, 0), -1)
        cv2.putText(annotated, label, (x1, y1 - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    
    return annotated

