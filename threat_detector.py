"""
threat_detector.py - Simplified After-Hours Threat Classifier
Replaces complex anomaly_detector.py with focused 3-level threat system

THREAT LEVELS:
- HIGH: Person detected after hours → ALERT
- MEDIUM: Vehicle or suspicious object after hours → ALERT  
- LOW: Animal detected → LOG ONLY (no alert)
"""

import json
from datetime import datetime, time
from typing import List, Dict, Any
from pathlib import Path


class ThreatDetector:
    """Simplified threat detection focused on after-hours activity"""
    
    def __init__(self, after_hours_start: int = 22, after_hours_end: int = 6):
        """
        Initialize threat detector
        
        Args:
            after_hours_start: Hour when after-hours begins (24hr format, default 22 = 10 PM)
            after_hours_end: Hour when after-hours ends (24hr format, default 6 = 6 AM)
        """
        self.after_hours_start = after_hours_start
        self.after_hours_end = after_hours_end
        
        # Threat classification rules
        self.threat_classes = {
            'HIGH': ['person'],
            'MEDIUM': ['car', 'truck', 'bus', 'motorcycle', 'bicycle', 
                      'backpack', 'suitcase', 'handbag'],
            'LOW': ['dog', 'cat', 'bird', 'horse']
        }
    
    def is_after_hours(self, frame_datetime: datetime) -> bool:
        """
        Check if timestamp falls within after-hours period
        
        Args:
            frame_datetime: Datetime object for frame
            
        Returns:
            True if after hours, False otherwise
        """
        hour = frame_datetime.hour
        
        # Handle overnight period (e.g., 22:00 - 06:00)
        if self.after_hours_start > self.after_hours_end:
            return hour >= self.after_hours_start or hour < self.after_hours_end
        else:
            return self.after_hours_start <= hour < self.after_hours_end
    
    def classify_threat(self, detected_class: str) -> Dict[str, Any]:
        """
        Classify a detected object into threat level
        
        Args:
            detected_class: YOLO class name (e.g., 'person', 'car', 'dog')
            
        Returns:
            Dict with threat level, alert flag, and reason
        """
        # Check HIGH threats
        if detected_class in self.threat_classes['HIGH']:
            return {
                'level': 'HIGH',
                'alert': True,
                'reason': f'{detected_class.title()} detected after hours'
            }
        
        # Check MEDIUM threats
        if detected_class in self.threat_classes['MEDIUM']:
            return {
                'level': 'MEDIUM',
                'alert': True,
                'reason': f'{detected_class.title()} detected after hours'
            }
        
        # Check LOW threats
        if detected_class in self.threat_classes['LOW']:
            return {
                'level': 'LOW',
                'alert': False,
                'reason': f'{detected_class.title()} detected (likely false alarm)'
            }
        
        # Unknown object - treat as LOW by default
        return {
            'level': 'LOW',
            'alert': False,
            'reason': f'Unknown object ({detected_class}) detected'
        }
    
    def analyze_detections(self, detection_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze detection results and generate threat reports
        
        Args:
            detection_results: List of detection dictionaries from detect_objects.py
                Each dict should have: frame_number, timestamp, detections[]
        
        Returns:
            List of threat dictionaries with level, alert, timestamp, etc.
        """
        threats = []
        
        for result in detection_results:
            frame_number = result.get('frame_number')
            frame_datetime = result.get('timestamp')
            detections = result.get('detections', [])
            
            # Skip if no timestamp or not after hours
            if not frame_datetime:
                continue
            
            if not self.is_after_hours(frame_datetime):
                continue  # Should already be filtered, but double-check
            
            # Process each detected object in this frame
            for detection in detections:
                detected_class = detection.get('class')
                confidence = detection.get('confidence', 0)
                bbox = detection.get('bbox', [])
                
                if not detected_class:
                    continue
                
                # Classify threat
                threat_info = self.classify_threat(detected_class)
                
                # Build threat record
                threat = {
                    'frame_number': frame_number,
                    'timestamp': frame_datetime.isoformat(),
                    'time_str': frame_datetime.strftime('%I:%M:%S %p'),
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