"""
cloud_pipeline.py - Cloud-Native CCTV Analysis Pipeline
Downloads from S3, processes with focused after-hours detection, uploads results
"""

import os
import sys
import json
import boto3
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Import local modules (upload these to EC2)
from detect_objects import AfterHoursDetector
from threat_detector import ThreatDetector
from extract_clips import extract_threat_clips


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/cloud_pipeline.log')
    ]
)
logger = logging.getLogger(__name__)


class CloudPipeline:
    """Cloud-aware CCTV analysis pipeline"""
    
    def __init__(self):
        """Initialize cloud pipeline with AWS clients"""
        load_dotenv()
        
        # AWS clients
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # Configuration
        self.footage_bucket = os.getenv('FOOTAGE_BUCKET')
        self.analysis_bucket = os.getenv('ANALYSIS_BUCKET')
        self.sns_topic_arn = os.getenv('SNS_TOPIC_ARN')
        
        self.after_hours_start = int(os.getenv('AFTER_HOURS_START', 22))
        self.after_hours_end = int(os.getenv('AFTER_HOURS_END', 6))
        self.confidence_threshold = float(os.getenv('PERSON_CONFIDENCE', 0.5))
        
        # Working directories
        self.work_dir = Path('/tmp/cctv_work')
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Cloud pipeline initialized")
        logger.info(f"Footage bucket: {self.footage_bucket}")
        logger.info(f"Analysis bucket: {self.analysis_bucket}")
        logger.info(f"After-hours: {self.after_hours_start}:00 - {self.after_hours_end}:00")
    
    def download_video(self, s3_key: str) -> Path:
        """
        Download video from S3
        
        Args:
            s3_key: S3 key for video file (e.g., 'camera-1/2025-01-15/video_233000.mp4')
            
        Returns:
            Path to downloaded video
        """
        logger.info(f"Downloading video: s3://{self.footage_bucket}/{s3_key}")
        
        local_path = self.work_dir / 'input_video.mp4'
        
        try:
            self.s3.download_file(
                self.footage_bucket,
                s3_key,
                str(local_path)
            )
            logger.info(f"Downloaded to: {local_path}")
            return local_path
        except Exception as e:
            logger.error(f"Failed to download video: {e}")
            raise
    
    def parse_video_datetime(self, s3_key: str) -> datetime:
        """
        Parse video datetime from S3 key
        Expected format: camera-id/YYYY-MM-DD/video_HHMMSS.mp4
        
        Args:
            s3_key: S3 key
            
        Returns:
            Datetime when video started
        """
        try:
            # Extract date and time from key
            # Example: camera-1/2025-01-15/video_233000.mp4
            parts = s3_key.split('/')
            date_str = parts[-2]  # 2025-01-15
            filename = parts[-1]  # video_233000.mp4
            
            time_str = filename.split('_')[1].split('.')[0]  # 233000
            
            # Parse datetime
            datetime_str = f"{date_str} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
            video_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            
            logger.info(f"Parsed video datetime: {video_datetime}")
            return video_datetime
            
        except Exception as e:
            logger.warning(f"Could not parse datetime from S3 key: {e}")
            # Fallback: use current time
            return datetime.now()
    
    def upload_results(self, output_dir: Path, s3_prefix: str):
        """
        Upload all results to S3
        
        Args:
            output_dir: Local directory with results
            s3_prefix: S3 prefix (e.g., 'camera-1/2025-01-15')
        """
        logger.info(f"Uploading results to s3://{self.analysis_bucket}/{s3_prefix}/")
        
        uploaded_count = 0
        
        for file_path in output_dir.rglob('*'):
            if file_path.is_file():
                # Calculate relative path
                relative_path = file_path.relative_to(output_dir)
                s3_key = f"{s3_prefix}/{relative_path}"
                
                try:
                    self.s3.upload_file(
                        str(file_path),
                        self.analysis_bucket,
                        s3_key
                    )
                    logger.debug(f"Uploaded: {s3_key}")
                    uploaded_count += 1
                except Exception as e:
                    logger.error(f"Failed to upload {s3_key}: {e}")
        
        logger.info(f"Uploaded {uploaded_count} files to S3")
    
    def cleanup_work_dir(self):
        """Clean up temporary files"""
        try:
            import shutil
            if self.work_dir.exists():
                shutil.rmtree(self.work_dir)
                logger.info("Cleaned up working directory")
        except Exception as e:
            logger.warning(f"Failed to cleanup: {e}")
    
    def process_video(self, s3_key: str) -> dict:
        """
        Complete processing pipeline for one video
        
        Args:
            s3_key: S3 key of video to process
            
        Returns:
            Processing summary
        """
        logger.info("="*60)
        logger.info("CLOUD PIPELINE STARTED")
        logger.info("="*60)
        
        start_time = datetime.now()
        
        try:
            # 1. Download video
            video_path = self.download_video(s3_key)
            video_datetime = self.parse_video_datetime(s3_key)
            
            # 2. Create output directory
            camera_id = s3_key.split('/')[0]
            date_str = video_datetime.strftime('%Y-%m-%d')
            timestamp = datetime.now().strftime('%H%M%S')
            
            output_dir = self.work_dir / 'results'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 3. Run detection (after-hours only)
            logger.info("Running object detection...")
            detector = AfterHoursDetector(
                model_path='yolov8n.pt',
                after_hours_start=self.after_hours_start,
                after_hours_end=self.after_hours_end,
                confidence_threshold=self.confidence_threshold
            )
            
            detection_results = detector.detect_objects_in_video(
                video_path=video_path,
                video_datetime=video_datetime,
                output_dir=output_dir,
                save_annotated=True,
                frame_skip=1
            )
            
            # 4. Threat classification
            logger.info("Classifying threats...")
            threat_detector = ThreatDetector(
                after_hours_start=self.after_hours_start,
                after_hours_end=self.after_hours_end
            )
            
            threats = threat_detector.analyze_detections(
                detection_results['detections']
            )
            threat_summary = threat_detector.generate_threat_summary(threats)
            
            threat_report_path = output_dir / 'threat_report.json'
            threat_detector.save_threat_report(threats, threat_report_path)
            
            # 5. Extract clips (HIGH/MEDIUM only)
            alert_threats = [t for t in threats if t['alert']]
            extracted_clips = []
            
            if alert_threats:
                logger.info(f"Extracting {len(alert_threats)} threat clips...")
                clips_dir = output_dir / 'flagged_clips'
                clips_dir.mkdir(exist_ok=True)
                
                extracted_clips = extract_threat_clips(
                    video_path=video_path,
                    threats=alert_threats,
                    output_dir=clips_dir,
                    clip_duration=30
                )
            
            # 6. Generate summary
            processing_time = (datetime.now() - start_time).total_seconds()
            
            summary = {
                'video_key': s3_key,
                'camera_id': camera_id,
                'video_datetime': video_datetime.isoformat(),
                'processed_at': datetime.now().isoformat(),
                'processing_time_seconds': round(processing_time, 1),
                'detection_summary': detection_results['summary'],
                'threat_summary': threat_summary,
                'clips_extracted': len(extracted_clips),
                'alerts_to_send': len(alert_threats)
            }
            
            summary_path = output_dir / 'summary.json'
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            
            # 7. Upload results to S3
            s3_prefix = f"{camera_id}/{date_str}"
            self.upload_results(output_dir, s3_prefix)
            
            # 8. Send alerts if needed
            if alert_threats and self.sns_topic_arn:
                from send_email_alerts import send_threat_alerts
                send_threat_alerts(
                    threats=alert_threats,
                    camera_id=camera_id,
                    video_datetime=video_datetime,
                    s3_bucket=self.analysis_bucket,
                    s3_prefix=s3_prefix,
                    sns_topic_arn=self.sns_topic_arn
                )
            
            # 9. Cleanup
            self.cleanup_work_dir()
            
            logger.info("="*60)
            logger.info("CLOUD PIPELINE COMPLETED")
            logger.info("="*60)
            logger.info(f"Processing time: {processing_time:.1f}s")
            logger.info(f"Threats detected: {threat_summary['total_threats']}")
            logger.info(f"Alerts sent: {len(alert_threats)}")
            logger.info(f"Results uploaded to: s3://{self.analysis_bucket}/{s3_prefix}/")
            
            return summary
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise


def main():
    """Run cloud pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CCTV Cloud Analysis Pipeline')
    parser.add_argument('s3_key', help='S3 key of video to process')
    parser.add_argument('--auto-shutdown', action='store_true', 
                       help='Shutdown EC2 instance after completion')
    
    args = parser.parse_args()
    
    try:
        # Run pipeline
        pipeline = CloudPipeline()
        results = pipeline.process_video(args.s3_key)
        
        logger.info("Pipeline completed successfully!")
        
        # Auto-shutdown if requested
        if args.auto_shutdown:
            logger.info("Auto-shutdown requested, terminating instance...")
            import subprocess
            instance_id = subprocess.check_output(
                ['ec2-metadata', '--instance-id']
            ).decode().split(':')[1].strip()
            
            ec2 = boto3.client('ec2')
            ec2.terminate_instances(InstanceIds=[instance_id])
            logger.info(f"Terminating instance: {instance_id}")
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()