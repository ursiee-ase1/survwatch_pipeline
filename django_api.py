"""
Django API Client Module
Handles communication with Django backend for cameras and alerts.
"""
import os
import requests
import base64
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DjangoAPIClient:
    """
    Client for communicating with Django surveillance backend.
    """
    
    def __init__(self, api_url: str = None, api_token: str = None):
        """
        Initialize Django API client.
        
        Args:
            api_url: Django API base URL (defaults to env var)
            api_token: API authentication token (defaults to env var)
        """
        self.api_url = (api_url or os.getenv('DJANGO_API_URL', 'http://localhost:8000')).rstrip('/')
        self.api_token = api_token or os.getenv('DJANGO_API_TOKEN', '')
        
        if not self.api_token:
            logger.warning("DJANGO_API_TOKEN not set - API calls may fail")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json',
        }
    
    def get_active_cameras(self) -> List[Dict]:
        """
        Fetch list of active cameras from Django.
        
        Returns:
            List of camera dictionaries with 'id' and 'rtsp_url'
        """
        try:
            url = f"{self.api_url}/api/active-cameras/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            
            cameras = response.json()
            logger.info(f"Fetched {len(cameras)} active cameras from Django")
            return cameras
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch cameras: {e}")
            return []
    
    def send_alert(self, camera_id: int, alert_type: str, confidence: float, 
                   image_frame=None, description: str = "") -> bool:
        """
        Send alert to Django backend.
        
        Args:
            camera_id: Camera ID from Django
            alert_type: Type of alert (intrusion, person, vehicle, etc.)
            confidence: Detection confidence (0.0-1.0)
            image_frame: OpenCV frame (numpy array) - optional
            description: Additional alert description
            
        Returns:
            True if alert sent successfully, False otherwise
        """
        try:
            url = f"{self.api_url}/api/send-alert/"
            
            # Convert frame to base64 if provided
            image_base64 = None
            if image_frame is not None:
                image_base64 = self._frame_to_base64(image_frame)
            
            payload = {
                'camera_id': camera_id,
                'alert_type': alert_type,
                'confidence': confidence,
                'image_base64': image_base64 or '',
                'description': description,
            }
            
            response = requests.post(url, json=payload, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            
            logger.info(f"✓ Alert sent to Django: camera {camera_id}, type: {alert_type}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send alert: {e}")
            return False
    
    def _frame_to_base64(self, frame) -> Optional[str]:
        """
        Convert OpenCV frame to base64-encoded JPEG string.
        
        Args:
            frame: OpenCV frame (numpy array)
            
        Returns:
            Base64-encoded image string or None on error
        """
        try:
            import cv2
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
            success, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            if not success:
                logger.error("Failed to encode frame")
                return None
            
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            return image_base64
            
        except Exception as e:
            logger.error(f"Error converting frame to base64: {e}")
            return None

