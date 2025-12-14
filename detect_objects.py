import cv2
from ultralytics import YOLO
from pathlib import Path
import json
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CCTVDetector:
    """CCTV video object detection pipeline"""
    
    def __init__(self, model_name='yolov8n.pt', conf_threshold=0.3):
        """
        Initialize detector
        
        Args:
            model_name: YOLO model to use (yolov8n.pt, yolov8s.pt, etc.)
            conf_threshold: Confidence threshold for detections (0-1)
        """
        print(f"Loading model: {model_name}...")
        self.model = YOLO(model_name)
        self.conf_threshold = conf_threshold
        print(f"✓ Model loaded (confidence threshold: {conf_threshold})")
    
    def process_video(self, video_path, output_dir, fps=1):
        """
        Process video and detect objects
        Supports both video files and RTSP streams.
        
        Args:
            video_path: Path to input video file OR RTSP URL
            output_dir: Directory to save results
            fps: Frames per second to process
            
        Returns:
            dict: Detection results with metadata
        """
        video_path = Path(video_path) if isinstance(video_path, (str, Path)) and not str(video_path).startswith('rtsp://') else str(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Open video (supports both files and RTSP)
        is_rtsp = isinstance(video_path, str) and video_path.startswith('rtsp://')
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        # Get video properties
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0  # Default to 30 if unknown
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if not is_rtsp else 0
        duration = total_frames / video_fps if total_frames > 0 else 0
        frame_skip = int(video_fps / fps) if video_fps > 0 else 30
        
        video_name = video_path.name if hasattr(video_path, 'name') else str(video_path)
        print(f"\n{'='*60}")
        print(f"Processing: {video_name}")
        if is_rtsp:
            print(f"RTSP Stream | FPS: {video_fps:.2f}")
        else:
            print(f"Duration: {duration:.2f}s | FPS: {video_fps:.2f}")
        print(f"Processing at: {fps} fps")
        print(f"{'='*60}\n")
        
        # Storage for detections
        all_detections = []
        frame_count = 0
        processed_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame at specified interval
            if frame_count % frame_skip == 0:
                timestamp = frame_count / video_fps
                
                # Run detection
                results = self.model(frame, conf=self.conf_threshold, verbose=False)
                
                # Parse detections
                frame_detections = self._parse_results(results[0], timestamp)
                
                if frame_detections['objects']:
                    all_detections.append(frame_detections)
                    
                    # Save annotated frame
                    annotated = results[0].plot()
                    frame_filename = f"frame_{processed_count:04d}_t{timestamp:.2f}s.jpg"
                    cv2.imwrite(str(output_dir / frame_filename), annotated)
                    
                    print(f"✓ Frame {processed_count:04d} @ {timestamp:.2f}s: "
                          f"{len(frame_detections['objects'])} objects detected")
                
                processed_count += 1
            
            frame_count += 1
        
        cap.release()
        
        # Compile results
        results = {
            'video_name': video_path.name,
            'video_path': str(video_path),
            'processed_at': datetime.now().isoformat(),
            'duration_seconds': duration,
            'total_frames': total_frames,
            'processed_frames': processed_count,
            'fps_processed': fps,
            'detections': all_detections,
            'summary': self._generate_summary(all_detections)
        }
        
        # Save JSON report
        report_path = output_dir / f"detection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"✓ Processing complete!")
        print(f"Frames processed: {processed_count}")
        print(f"Detections: {len(all_detections)} frames with objects")
        print(f"Report saved: {report_path.name}")
        print(f"{'='*60}\n")
        
        return results
    
    def _parse_results(self, result, timestamp):
        """Parse YOLO results into structured format"""
        objects = []
        
        for box in result.boxes:
            obj = {
                'class': result.names[int(box.cls)],
                'confidence': float(box.conf),
                'bbox': box.xyxy[0].tolist(),  # [x1, y1, x2, y2]
            }
            objects.append(obj)
        
        return {
            'timestamp': timestamp,
            'objects': objects,
            'object_count': len(objects)
        }
    
    def _generate_summary(self, detections):
        """Generate summary statistics"""
        if not detections:
            return {'total_objects': 0, 'unique_classes': []}
        
        all_objects = [obj for d in detections for obj in d['objects']]
        class_counts = {}
        
        for obj in all_objects:
            cls = obj['class']
            class_counts[cls] = class_counts.get(cls, 0) + 1
        
        return {
            'total_objects': len(all_objects),
            'unique_classes': list(class_counts.keys()),
            'class_counts': class_counts,
            'frames_with_detections': len(detections)
        }


class AfterHoursDetector:
    """
    After-hours focused detector that only processes frames during after-hours period
    Skips business hours to save processing time
    """
    
    def __init__(self, model_path='yolov8n.pt', after_hours_start=22, after_hours_end=6, confidence_threshold=0.3):
        """
        Initialize after-hours detector
        
        Args:
            model_path: Path to YOLO model file
            after_hours_start: Hour when after-hours begins (24hr format, default 22 = 10 PM)
            after_hours_end: Hour when after-hours ends (24hr format, default 6 = 6 AM)
            confidence_threshold: Confidence threshold for detections (0-1)
        """
        self.detector = CCTVDetector(model_name=model_path, conf_threshold=confidence_threshold)
        self.after_hours_start = after_hours_start
        self.after_hours_end = after_hours_end
        self.confidence_threshold = confidence_threshold
    
    def _is_after_hours(self, frame_datetime):
        """Check if timestamp falls within after-hours period"""
        hour = frame_datetime.hour
        
        # Handle overnight period (e.g., 22:00 - 06:00)
        if self.after_hours_start > self.after_hours_end:
            return hour >= self.after_hours_start or hour < self.after_hours_end
        else:
            return self.after_hours_start <= hour < self.after_hours_end
    
    def detect_objects_in_video(self, video_path, video_datetime, output_dir, save_annotated=True, frame_skip=1):
        """
        Detect objects in video, processing only after-hours frames
        
        Args:
            video_path: Path to input video
            video_datetime: Datetime when video recording started
            output_dir: Directory to save results
            save_annotated: Whether to save annotated frames
            frame_skip: Process every Nth frame (1 = every frame in after-hours)
            
        Returns:
            dict: Detection results with detections list and summary
        """
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        # Get video properties
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / video_fps
        
        print(f"\n{'='*60}")
        print(f"After-Hours Detection: {video_path.name}")
        print(f"Video duration: {duration:.2f}s | FPS: {video_fps:.2f}")
        print(f"After-hours: {self.after_hours_start}:00 - {self.after_hours_end}:00")
        print(f"Processing every {frame_skip} frame in after-hours only")
        print(f"{'='*60}\n")
        
        # Storage for detections
        all_detections = []
        frame_count = 0
        processed_count = 0
        skipped_business_hours = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate frame timestamp
            frame_timestamp = video_datetime + timedelta(seconds=frame_count / video_fps)
            
            # Skip if not after hours
            if not self._is_after_hours(frame_timestamp):
                skipped_business_hours += 1
                frame_count += 1
                continue
            
            # Process frame at specified interval
            if frame_count % frame_skip == 0:
                # Run detection
                results = self.detector.model(frame, conf=self.confidence_threshold, verbose=False)
                
                # Parse detections
                frame_detections = self.detector._parse_results(results[0], frame_count / video_fps)
                
                if frame_detections['objects']:
                    # Format for threat_detector compatibility
                    detection_record = {
                        'frame_number': frame_count,
                        'timestamp': frame_timestamp,
                        'detections': frame_detections['objects']
                    }
                    all_detections.append(detection_record)
                    
                    # Save annotated frame if requested
                    if save_annotated:
                        annotated = results[0].plot()
                        frame_filename = f"frame_{processed_count:04d}_t{frame_count/video_fps:.2f}s.jpg"
                        cv2.imwrite(str(output_dir / frame_filename), annotated)
                    
                    print(f"✓ Frame {processed_count:04d} @ {frame_timestamp.strftime('%H:%M:%S')}: "
                          f"{len(frame_detections['objects'])} objects detected")
                
                processed_count += 1
            
            frame_count += 1
        
        cap.release()
        
        # Generate summary
        total_objects = sum(len(d['detections']) for d in all_detections)
        unique_classes = set()
        for d in all_detections:
            for obj in d['detections']:
                unique_classes.add(obj['class'])
        
        summary = {
            'total_frames': total_frames,
            'frames_processed': processed_count,
            'frames_skipped_business_hours': skipped_business_hours,
            'processing_efficiency_pct': (processed_count / total_frames * 100) if total_frames > 0 else 0,
            'objects_detected': total_objects,
            'unique_classes': list(unique_classes)
        }
        
        # Save detection report
        report_path = output_dir / f"detection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            'video_name': video_path.name,
            'video_path': str(video_path),
            'video_start_time': video_datetime.isoformat(),
            'processed_at': datetime.now().isoformat(),
            'after_hours_config': {
                'start': self.after_hours_start,
                'end': self.after_hours_end
            },
            'summary': summary,
            'detections': all_detections
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"✓ Processing complete!")
        print(f"Frames processed: {processed_count} (skipped {skipped_business_hours} business hours)")
        print(f"Time saved: {100 - summary['processing_efficiency_pct']:.1f}%")
        print(f"Objects detected: {total_objects}")
        print(f"Report saved: {report_path.name}")
        print(f"{'='*60}\n")
        
        return {
            'detections': all_detections,
            'summary': summary,
            'report_path': report_path
        }


if __name__ == "__main__":
    # Test detection
    detector = CCTVDetector(conf_threshold=0.3)
    
    video = "C:/cctv-analysis/data/test_video.mp4"
    output = "C:/cctv-analysis/data/detections"
    
    if Path(video).exists():
        results = detector.process_video(video, output, fps=1)
        
        print("\nSummary:")
        print(f"  Total objects detected: {results['summary']['total_objects']}")
        print(f"  Classes found: {', '.join(results['summary']['unique_classes'])}")
    else:
        print(f"✗ Video not found: {video}")