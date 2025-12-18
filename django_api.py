"""
Django API Client Module
Handles communication with Django backend for cameras and alerts.
"""
import os
import requests
import base64
import logging
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DjangoAPIClient:
    """
    Client for communicating with Django surveillance backend.
    Includes caching for detection configs to reduce API calls.
    """
    
    def __init__(self, api_url: str = None, api_token: str = None, config_cache_ttl: int = 120):
        """
        Initialize Django API client.
        
        Args:
            api_url: Django API base URL (defaults to env var)
            api_token: API authentication token (defaults to env var)
            config_cache_ttl: Config cache TTL in seconds (default 120)
        """
        self.api_url = (api_url or os.getenv('DJANGO_API_URL', 'http://localhost:8000')).rstrip('/')
        self.api_token = api_token or os.getenv('DJANGO_API_TOKEN', '')
        self.config_cache_ttl = config_cache_ttl
        
        # In-memory cache for detection configs: {camera_id: (config_data, timestamp)}
        self._config_cache: Dict[int, tuple] = {}
        
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
        Fetch list of active cameras from Django with effective detection configs.
        
        Returns:
            List of camera dictionaries with 'id', 'rtsp_url', 'name', and 'effective_config'
        """
        try:
            url = f"{self.api_url}/api/active-cameras/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            
            cameras = response.json()
            logger.info(f"Fetched {len(cameras)} active cameras from Django")
            
            # Update cache with fresh configs
            current_time = time.time()
            for camera in cameras:
                camera_id = camera.get('id')
                if camera_id and 'effective_config' in camera:
                    self._config_cache[camera_id] = (camera['effective_config'], current_time)
            
            return cameras
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch cameras: {e}")
            # Return cached configs if available
            return self._get_cached_cameras()
    
    def _get_cached_cameras(self) -> List[Dict]:
        """Get cameras from cache if API is unreachable."""
        cached = []
        for camera_id, (config, _) in self._config_cache.items():
            cached.append({
                'id': camera_id,
                'rtsp_url': '',  # Can't get from cache
                'name': f'Camera {camera_id}',
                'effective_config': config,
            })
        if cached:
            logger.warning(f"Using cached configs for {len(cached)} cameras (backend unreachable)")
        return cached
    
    def get_camera_config(self, camera_id: int) -> Optional[Dict]:
        """
        Get detection config for a specific camera (with caching).
        
        Args:
            camera_id: Camera ID
            
        Returns:
            Detection config dict or None if not found
        """
        # Check cache first
        if camera_id in self._config_cache:
            config_data, cache_time = self._config_cache[camera_id]
            if time.time() - cache_time < self.config_cache_ttl:
                return config_data
        
        # Fetch from API
        try:
            url = f"{self.api_url}/api/cameras/{camera_id}/config/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            
            config = response.json()
            self._config_cache[camera_id] = (config, time.time())
            return config
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch config for camera {camera_id}: {e}")
            # Return cached config if available
            if camera_id in self._config_cache:
                config_data, _ = self._config_cache[camera_id]
                logger.info(f"Using cached config for camera {camera_id}")
                return config_data
            
            # Return safe defaults
            logger.warning(f"No config available for camera {camera_id}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get safe default detection config."""
        return {
            'monitor_mode': 'after_hours',
            'active_hours_start': '09:00:00',
            'active_hours_end': '17:00:00',
            'timezone': 'UTC',
            'confidence_threshold': 0.6,
            'frame_skip': 30,
            'rules': [],
        }
    
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

