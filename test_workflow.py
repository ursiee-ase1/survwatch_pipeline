import os
from pathlib import Path
from dotenv import load_dotenv
from upload_to_s3 import upload_video_to_s3, list_s3_videos
from download_from_s3 import download_video_from_s3
from extract_frames import extract_frames
from datetime import datetime

# Test YOLOv8 on frames
from ultralytics import YOLO
import cv2

load_dotenv("C:/cctv-analysis/.env")

def run_workflow_test():
    """Test complete workflow: Upload → Download → Extract → Detect"""
    
    print("\n" + "="*70)
    print("CCTV ANALYSIS WORKFLOW TEST")
    print("="*70)
    
    # Configuration
    bucket = os.getenv("FOOTAGE_BUCKET")
    test_video = "C:/cctv-analysis/data/test_video.mp4"
    camera_id = "camera-test"
    date = datetime.now().strftime("%Y-%m-%d")
    
    if not bucket:
        print("✗ FOOTAGE_BUCKET not set. Run bucket creation first!")
        return False
    
    if not os.path.exists(test_video):
        print(f"✗ Test video not found: {test_video}")
        return False
    
    try:
        # STEP 1: Upload to S3
        print("\n[1/5] Uploading video to S3...")
        s3_key = f"{camera_id}/{date}/test_video.mp4"
        upload_video_to_s3(test_video, bucket, camera_id, date)
        
        # STEP 2: List S3 contents
        print("\n[2/5] Verifying S3 upload...")
        list_s3_videos(bucket, camera_id)
        
        # STEP 3: Download from S3
        print("\n[3/5] Downloading from S3...")
        download_dir = "C:/cctv-analysis/data/workflow_test"
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        downloaded_video = download_video_from_s3(
            bucket, s3_key, f"{download_dir}/downloaded_video.mp4"
        )
        
        # STEP 4: Extract frames
        print("\n[4/5] Extracting frames...")
        frames_dir = f"{download_dir}/frames"
        extract_frames(downloaded_video, frames_dir, fps=1, max_frames=5)
        
        # STEP 5: Run YOLOv8 detection
        print("\n[5/5] Running object detection...")
        model = YOLO('yolov8n.pt')
        
        frame_files = sorted(Path(frames_dir).glob("*.jpg"))
        if frame_files:
            test_frame = str(frame_files[0])
            results = model(test_frame)
            
            # Count detections
            detections = len(results[0].boxes)
            print(f"✓ Detected {detections} objects in frame")
            
            # Save result
            output = f"{download_dir}/detection_result.jpg"
            img = cv2.imread(test_frame)
            img = results[0].plot()
            cv2.imwrite(output, img)
            print(f"✓ Saved detection result: {output}")
        
        print("\n" + "="*70)
        print("✓ WORKFLOW TEST COMPLETE!")
        print("="*70)
        print(f"\nResults in: {download_dir}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_workflow_test()
    exit(0 if success else 1)