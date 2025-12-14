"""
run_pipeline.py - Focused After-Hours Threat Detection Pipeline
Orchestrates: Detection (after-hours only) → Threat Classification → Clip Extraction
"""

import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Import our modules
from detect_objects import AfterHoursDetector
from threat_detector import ThreatDetector
from extract_clips import extract_threat_clips


def run_focused_pipeline(video_path: Path, 
                        video_datetime: datetime,
                        output_dir: Path = None,
                        save_annotated: bool = True) -> dict:
    """
    Run complete focused threat detection pipeline
    
    Pipeline steps:
    1. YOLOv8 detection (skip business hours, process only after-hours)
    2. Threat classification (HIGH/MEDIUM/LOW)
    3. Clip extraction (only HIGH/MEDIUM threats)
    4. Generate reports
    
    Args:
        video_path: Path to video file
        video_datetime: When video recording started
        output_dir: Where to save results (auto-generated if None)
        save_annotated: Whether to save annotated frames
        
    Returns:
        Dictionary with pipeline results and metrics
    """
    print("=" * 60)
    print("🚀 FOCUSED AFTER-HOURS THREAT DETECTION PIPELINE")
    print("=" * 60)
    
    # Load configuration
    load_dotenv()
    after_hours_start = int(os.getenv('AFTER_HOURS_START', 22))
    after_hours_end = int(os.getenv('AFTER_HOURS_END', 6))
    person_confidence = float(os.getenv('PERSON_CONFIDENCE', 0.5))
    
    # Create output directory
    if output_dir is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path('data/pipeline_runs') / f"run_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📁 Output directory: {output_dir}")
    print(f"⏰ After-hours: {after_hours_start}:00 - {after_hours_end}:00")
    print(f"🎯 Confidence threshold: {person_confidence}")
    
    # ============================================================
    # STEP 1: Object Detection (After-Hours Only)
    # ============================================================
    print(f"\n{'='*60}")
    print("STEP 1: YOLOv8 Object Detection (After-Hours Filtering)")
    print(f"{'='*60}")
    
    detector = AfterHoursDetector(
        model_path='yolov8n.pt',
        after_hours_start=after_hours_start,
        after_hours_end=after_hours_end,
        confidence_threshold=person_confidence
    )
    
    detection_results = detector.detect_objects_in_video(
        video_path=video_path,
        video_datetime=video_datetime,
        output_dir=output_dir,
        save_annotated=save_annotated,
        frame_skip=1  # Process every frame in after-hours
    )
    
    detections = detection_results['detections']
    detection_summary = detection_results['summary']
    
    # ============================================================
    # STEP 2: Threat Classification
    # ============================================================
    print(f"\n{'='*60}")
    print("STEP 2: Threat Classification (HIGH/MEDIUM/LOW)")
    print(f"{'='*60}")
    
    threat_detector = ThreatDetector(
        after_hours_start=after_hours_start,
        after_hours_end=after_hours_end
    )
    
    threats = threat_detector.analyze_detections(detections)
    threat_summary = threat_detector.generate_threat_summary(threats)
    
    # Save threat report
    threat_report_path = output_dir / 'threat_report.json'
    threat_detector.save_threat_report(threats, threat_report_path)
    
    print(f"\n📊 Threat Summary:")
    print(f"   Total threats: {threat_summary['total_threats']}")
    print(f"   HIGH threats: {threat_summary['high_threats']}")
    print(f"   MEDIUM threats: {threat_summary['medium_threats']}")
    print(f"   LOW threats: {threat_summary['low_threats']}")
    print(f"   Alerts to send: {threat_summary['alerts_triggered']}")
    
    if threat_summary['threat_breakdown']:
        print(f"\n   Threat breakdown:")
        for obj_class, info in threat_summary['threat_breakdown'].items():
            print(f"     - {obj_class}: {info['count']} ({info['level']} threat)")
    
    # ============================================================
    # STEP 3: Extract Clips (Only HIGH/MEDIUM Threats)
    # ============================================================
    print(f"\n{'='*60}")
    print("STEP 3: Clip Extraction (HIGH/MEDIUM Threats Only)")
    print(f"{'='*60}")
    
    # Filter for alert-worthy threats
    alert_threats = [t for t in threats if t['alert']]
    
    if alert_threats:
        print(f"✂️  Extracting {len(alert_threats)} clips for HIGH/MEDIUM threats...")
        
        clips_dir = output_dir / 'flagged_clips'
        clips_dir.mkdir(exist_ok=True)
        
        extracted_clips = extract_threat_clips(
            video_path=video_path,
            threats=alert_threats,
            output_dir=clips_dir,
            clip_duration=30  # 30 seconds per clip
        )
        
        print(f"✅ Extracted {len(extracted_clips)} clips")
    else:
        print("✅ No HIGH/MEDIUM threats detected - no clips to extract")
        extracted_clips = []
    
    # ============================================================
    # STEP 4: Generate Final Summary
    # ============================================================
    print(f"\n{'='*60}")
    print("STEP 4: Pipeline Summary")
    print(f"{'='*60}")
    
    pipeline_summary = {
        'run_timestamp': datetime.now().isoformat(),
        'video_path': str(video_path),
        'video_start_time': video_datetime.isoformat(),
        'output_dir': str(output_dir),
        'after_hours_config': {
            'start': after_hours_start,
            'end': after_hours_end
        },
        'detection': {
            'total_frames': detection_summary['total_frames'],
            'business_hours_skipped': detection_summary['frames_skipped_business_hours'],
            'after_hours_processed': detection_summary['frames_processed'],
            'efficiency_pct': detection_summary['processing_efficiency_pct'],
            'objects_detected': detection_summary['objects_detected']
        },
        'threats': {
            'total': threat_summary['total_threats'],
            'high': threat_summary['high_threats'],
            'medium': threat_summary['medium_threats'],
            'low': threat_summary['low_threats'],
            'alerts': threat_summary['alerts_triggered'],
            'breakdown': threat_summary['threat_breakdown']
        },
        'clips': {
            'extracted': len(extracted_clips),
            'clip_paths': [str(clip) for clip in extracted_clips]
        },
        'reports': {
            'detection_report': str(detection_results['report_path']),
            'threat_report': str(threat_report_path)
        }
    }
    
    # Save pipeline summary
    summary_path = output_dir / 'summary.json'
    with open(summary_path, 'w') as f:
        json.dump(pipeline_summary, f, indent=2)
    
    # Print final results
    print(f"\n✅ Pipeline Complete!")
    print(f"\n📊 Results:")
    print(f"   Frames processed: {detection_summary['frames_processed']}/{detection_summary['total_frames']}")
    print(f"   Time saved: {100 - detection_summary['processing_efficiency_pct']:.1f}% (business hours skipped)")
    print(f"   Threats detected: {threat_summary['total_threats']}")
    print(f"   Alerts to send: {threat_summary['alerts_triggered']}")
    print(f"   Clips extracted: {len(extracted_clips)}")
    print(f"\n📁 All results saved to: {output_dir}")
    print(f"   - Detection report: detection_report.json")
    print(f"   - Threat report: threat_report.json")
    print(f"   - Summary: summary.json")
    if extracted_clips:
        print(f"   - Clips: flagged_clips/ ({len(extracted_clips)} files)")
    
    return pipeline_summary


def main():
    """Run pipeline with test video"""
    
    # Configuration - UPDATE THESE FOR YOUR TEST
    video_path = Path('data/samples/test_video.mp4')
    
    # IMPORTANT: Set video datetime to after-hours for testing
    # Example scenarios:
    # - Late night: datetime(2025, 1, 15, 23, 30, 0)  # 11:30 PM
    # - Early morning: datetime(2025, 1, 16, 2, 15, 0)  # 2:15 AM
    # - Business hours (should skip most frames): datetime(2025, 1, 15, 14, 0, 0)  # 2:00 PM
    
    video_datetime = datetime(2025, 1, 15, 23, 30, 0)  # 11:30 PM
    
    # Check if video exists
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        print("\nPlease ensure you have a test video at:")
        print(f"   {video_path.absolute()}")
        print("\nYou can:")
        print("   1. Place any MP4 video at that location")
        print("   2. Use footage from a CCTV camera")
        print("   3. Use a test video with people/vehicles visible")
        return
    
    # Run pipeline
    try:
        results = run_focused_pipeline(
            video_path=video_path,
            video_datetime=video_datetime,
            save_annotated=True
        )
        
        print("\n" + "="*60)
        print("🎉 SUCCESS! Pipeline completed successfully")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        raise


if __name__ == '__main__':
    main()