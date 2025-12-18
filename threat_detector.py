"""
threat_detector.py - Backend-Driven Threat Classifier
Uses detection rules from Django backend instead of hardcoded logic.

THREAT LEVELS (from backend):
- HIGH: Always alert
- MEDIUM: Alert (lower priority)
- LOW: Log only
- IGNORE: Discard completely
"""

import json
from datetime import datetime, time
from typing import List, Dict, Any, Optional
from pathlib import Path
import pytz
import logging

logger = logging.getLogger(__name__)


class ThreatDetector:
    """
    Threat detection using backend-driven configuration.
    No hardcoded rules - all detection behavior comes from Django API.
    """
    
    def __init__(self, detection_config: Optional[Dict] = None):
        """
        Initialize threat detector with backend config.
        
        Args:
            detection_config: Detection config dict from Django API
                {
                    'monitor_mode': 'after_hours' | 'always' | 'custom',
                    'active_hours_start': 'HH:MM:SS',
                    'active_hours_end': 'HH:MM:SS',
                    'timezone': 'America/New_York' | 'UTC' | etc,
                    'confidence_threshold': 0.6,
                    'frame_skip': 30,
                    'rules': [
                        {
                            'object_class': 'person',
                            'threat_level': 'HIGH',
                            'should_alert': True,
                            'min_confidence': 0.7
                        },
                        ...
                    ]
                }
        """
        self.config = detection_config or self._get_default_config()
        self._parse_config()
    
    def _get_default_config(self) -> Dict:
        """Get safe default config if backend is unreachable."""
        return {
            'monitor_mode': 'after_hours',
            'active_hours_start': '09:00:00',
            'active_hours_end': '17:00:00',
            'timezone': 'UTC',
            'confidence_threshold': 0.6,
            'frame_skip': 30,
            'rules': [],
        }
    
    def _parse_config(self):
        """Parse config into usable format."""
        # Parse time strings
        self.active_hours_start = datetime.strptime(
            self.config.get('active_hours_start', '09:00:00'), 
            '%H:%M:%S'
        ).time()
        self.active_hours_end = datetime.strptime(
            self.config.get('active_hours_end', '17:00:00'), 
            '%H:%M:%S'
        ).time()
        
        self.monitor_mode = self.config.get('monitor_mode', 'after_hours')
        self.timezone_str = self.config.get('timezone', 'UTC')
        self.confidence_threshold = self.config.get('confidence_threshold', 0.6)
        self.frame_skip = self.config.get('frame_skip', 30)
        
        # Build rule lookup: {object_class: rule_dict}
        self.rules: Dict[str, Dict] = {}
        for rule in self.config.get('rules', []):
            obj_class = rule.get('object_class')
            if obj_class:
                self.rules[obj_class] = {
                    'threat_level': rule.get('threat_level', 'LOW'),
                    'should_alert': rule.get('should_alert', False),
                    'min_confidence': rule.get('min_confidence') or self.confidence_threshold,
                }
        
        logger.info(f"ThreatDetector initialized: mode={self.monitor_mode}, "
                   f"rules={len(self.rules)}, threshold={self.confidence_threshold}")
    
    def update_config(self, new_config: Dict):
        """Update detection config (called when backend config changes)."""
        self.config = new_config
        self._parse_config()
        logger.info("ThreatDetector config updated")
    
    def should_process_frame(self, frame_datetime: datetime) -> bool:
        """
        Check if frame should be processed based on monitor mode and time.
        
        Args:
            frame_datetime: Datetime object for frame (assumed to be in camera timezone)
            
        Returns:
            True if frame should be processed, False otherwise
        """
        if self.monitor_mode == 'always':
            return True
        
        # Get current time in camera timezone
        try:
            tz = pytz.timezone(self.timezone_str)
            if frame_datetime.tzinfo is None:
                # Assume UTC if no timezone info
                frame_datetime = pytz.utc.localize(frame_datetime)
            local_time = frame_datetime.astimezone(tz).time()
        except Exception as e:
            logger.warning(f"Timezone conversion error: {e}, using UTC")
            local_time = frame_datetime.time()
        
        current_time = local_time
        
        if self.monitor_mode == 'after_hours':
            # Process only outside active hours
            if self.active_hours_start < self.active_hours_end:
                # Normal case: 09:00 - 17:00
                return not (self.active_hours_start <= current_time < self.active_hours_end)
            else:
                # Overnight case: e.g., 17:00 - 09:00
                return not (current_time >= self.active_hours_start or current_time < self.active_hours_end)
        
        elif self.monitor_mode == 'custom':
            # For now, same as after_hours (can be extended for multiple windows)
            if self.active_hours_start < self.active_hours_end:
                return not (self.active_hours_start <= current_time < self.active_hours_end)
            else:
                return not (current_time >= self.active_hours_start or current_time < self.active_hours_end)
        
        return True
    
    def classify_threat(self, detected_class: str, confidence: float) -> Dict[str, Any]:
        """
        Classify a detected object using backend-driven rules.
        
        Args:
            detected_class: YOLO class name (e.g., 'person', 'car', 'dog')
            confidence: Detection confidence (0.0-1.0)
            
        Returns:
            Dict with threat level, alert flag, and reason
        """
        # Check if we have a rule for this object class
        rule = self.rules.get(detected_class)
        
        if not rule:
            # No rule defined - treat as IGNORE (don't alert)
            return {
                'level': 'IGNORE',
                'alert': False,
                'reason': f'{detected_class.title()} not configured for detection'
            }
        
        # Check confidence threshold
        min_conf = rule.get('min_confidence', self.confidence_threshold)
        if confidence < min_conf:
            return {
                'level': rule['threat_level'],
                'alert': False,
                'reason': f'{detected_class.title()} detected but confidence ({confidence:.2f}) below threshold ({min_conf:.2f})'
            }
        
        threat_level = rule.get('threat_level', 'LOW')
        should_alert = rule.get('should_alert', False)
        
        # Map threat levels to alert behavior
        if threat_level == 'IGNORE':
            should_alert = False
        elif threat_level == 'HIGH':
            should_alert = True
        elif threat_level == 'MEDIUM':
            should_alert = should_alert  # Use rule setting
        elif threat_level == 'LOW':
            should_alert = False  # LOW never alerts
        
        return {
            'level': threat_level,
            'alert': should_alert,
            'reason': f'{detected_class.title()} detected ({threat_level} threat)'
        }
    
    def analyze_detections(self, detection_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze detection results using backend-driven rules.
        
        Args:
            detection_results: List of detection dictionaries
                Each dict should have: frame_number, timestamp, detections[]
        
        Returns:
            List of threat dictionaries with level, alert, timestamp, etc.
        """
        threats = []
        
        for result in detection_results:
            frame_number = result.get('frame_number')
            frame_datetime = result.get('timestamp')
            detections = result.get('detections', [])
            
            # Skip if no timestamp
            if not frame_datetime:
                continue
            
            # Check if frame should be processed based on monitor mode
            if not self.should_process_frame(frame_datetime):
                continue  # Skip business hours if in after_hours mode
            
            # Process each detected object in this frame
            for detection in detections:
                detected_class = detection.get('class')
                confidence = detection.get('confidence', 0)
                bbox = detection.get('bbox', [])
                
                if not detected_class:
                    continue
                
                # Classify threat using backend rules
                threat_info = self.classify_threat(detected_class, confidence)
                
                # Skip IGNORE level threats
                if threat_info['level'] == 'IGNORE':
                    continue
                
                # Build threat record
                threat = {
                    'frame_number': frame_number,
                    'timestamp': frame_datetime.isoformat() if isinstance(frame_datetime, datetime) else str(frame_datetime),
                    'time_str': frame_datetime.strftime('%I:%M:%S %p') if isinstance(frame_datetime, datetime) else str(frame_datetime),
                    'detected_class': detected_class,
                    'confidence': round(confidence, 2),
                    'bbox': bbox,
                    'threat_level': threat_info['level'],
                    'alert': threat_info['alert'],
                    'reason': threat_info['reason']
                }
                
                threats.append(threat)
        
        return threats
    
    def generate_threat_summary(self, threats: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics for detected threats
        
        Args:
            threats: List of threat dictionaries
            
        Returns:
            Summary dictionary with counts and statistics
        """
        high_threats = [t for t in threats if t['threat_level'] == 'HIGH']
        medium_threats = [t for t in threats if t['threat_level'] == 'MEDIUM']
        low_threats = [t for t in threats if t['threat_level'] == 'LOW']
        alert_threats = [t for t in threats if t['alert']]
        
        summary = {
            'total_threats': len(threats),
            'high_threats': len(high_threats),
            'medium_threats': len(medium_threats),
            'low_threats': len(low_threats),
            'alerts_triggered': len(alert_threats),
            'threat_breakdown': {},
            'first_threat': None,
            'last_threat': None
        }
        
        # Count threats by detected class
        for threat in threats:
            detected_class = threat['detected_class']
            if detected_class not in summary['threat_breakdown']:
                summary['threat_breakdown'][detected_class] = {
                    'count': 0,
                    'level': threat['threat_level']
                }
            summary['threat_breakdown'][detected_class]['count'] += 1
        
        # Add first/last threat timestamps
        if threats:
            summary['first_threat'] = threats[0]['time_str']
            summary['last_threat'] = threats[-1]['time_str']
        
        return summary
    
    def save_threat_report(self, threats: List[Dict[str, Any]], output_path: Path):
        """
        Save threat analysis to JSON file
        
        Args:
            threats: List of threat dictionaries
            output_path: Path to save report
        """
        summary = self.generate_threat_summary(threats)
        
        report = {
            'summary': summary,
            'threats': threats
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Threat report saved: {output_path}")
        return report


def main():
    """Test threat detector with sample data"""
    from datetime import datetime, timedelta
    
    detector = ThreatDetector(after_hours_start=22, after_hours_end=6)
    
    # Test after-hours detection
    test_times = [
        datetime(2025, 1, 15, 23, 30),  # 11:30 PM - after hours
        datetime(2025, 1, 15, 14, 0),   # 2:00 PM - business hours
        datetime(2025, 1, 16, 3, 15),   # 3:15 AM - after hours
    ]
    
    print("After-hours check:")
    for dt in test_times:
        is_after = detector.is_after_hours(dt)
        print(f"  {dt.strftime('%I:%M %p')} - {'AFTER HOURS' if is_after else 'Business hours'}")
    
    # Test threat classification
    print("\nThreat classification:")
    test_objects = ['person', 'car', 'dog', 'backpack', 'unknown']
    for obj in test_objects:
        threat = detector.classify_threat(obj)
        print(f"  {obj}: {threat['level']} - Alert: {threat['alert']}")
    
    # Test full analysis
    print("\nFull analysis test:")
    sample_detections = [
        {
            'frame_number': 100,
            'timestamp': datetime(2025, 1, 15, 23, 30),
            'detections': [
                {'class': 'person', 'confidence': 0.85, 'bbox': [100, 100, 200, 300]}
            ]
        },
        {
            'frame_number': 200,
            'timestamp': datetime(2025, 1, 16, 2, 15),
            'detections': [
                {'class': 'car', 'confidence': 0.78, 'bbox': [300, 150, 500, 350]},
                {'class': 'dog', 'confidence': 0.65, 'bbox': [50, 200, 150, 400]}
            ]
        }
    ]
    
    threats = detector.analyze_detections(sample_detections)
    summary = detector.generate_threat_summary(threats)
    
    print(f"  Total threats: {summary['total_threats']}")
    print(f"  HIGH: {summary['high_threats']}, MEDIUM: {summary['medium_threats']}, LOW: {summary['low_threats']}")
    print(f"  Alerts to send: {summary['alerts_triggered']}")
    print(f"  Threat breakdown: {summary['threat_breakdown']}")


if __name__ == '__main__':
    main()