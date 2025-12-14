import boto3
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv("C:/cctv-analysis/.env")

def upload_video_to_s3(video_path, bucket_name, camera_id="camera-01", date=None):
    """
    Upload video to S3 with organized structure
    
    Args:
        video_path: Local path to video file
        bucket_name: S3 bucket name
        camera_id: Camera identifier (default: camera-01)
        date: Date string (YYYY-MM-DD) or None for today
    """
    video_path = Path(video_path)
    
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    # Generate date if not provided
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Construct S3 key with folder structure
    s3_key = f"{camera_id}/{date}/{video_path.name}"
    
    # Initialize S3 client
    s3 = boto3.client('s3', region_name='us-east-1')
    
    print(f"\n{'='*60}")
    print(f"Uploading to S3...")
    print(f"Bucket: {bucket_name}")
    print(f"Key: {s3_key}")
    print(f"File: {video_path.name} ({video_path.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"{'='*60}\n")
    
    try:
        # Upload with metadata
        s3.upload_file(
            str(video_path),
            bucket_name,
            s3_key,
            ExtraArgs={
                'Metadata': {
                    'camera-id': camera_id,
                    'upload-date': datetime.now().isoformat(),
                    'original-filename': video_path.name
                },
                'Tagging': f'CameraID={camera_id}&UploadDate={date}'
            }
        )
        
        print(f"✓ Upload successful!")
        print(f"S3 URI: s3://{bucket_name}/{s3_key}")
        
        return f"s3://{bucket_name}/{s3_key}"
        
    except Exception as e:
        print(f"✗ Upload failed: {e}")
        raise

def list_s3_videos(bucket_name, camera_id=None):
    """List all videos in S3 bucket"""
    s3 = boto3.client('s3', region_name='us-east-1')
    
    prefix = f"{camera_id}/" if camera_id else ""
    
    print(f"\n{'='*60}")
    print(f"Videos in s3://{bucket_name}/{prefix}")
    print(f"{'='*60}\n")
    
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        
        if 'Contents' not in response:
            print("No videos found")
            return []
        
        videos = []
        for obj in response['Contents']:
            size_mb = obj['Size'] / 1024 / 1024
            print(f"✓ {obj['Key']} ({size_mb:.2f} MB)")
            videos.append(obj['Key'])
        
        print(f"\nTotal: {len(videos)} files")
        return videos
        
    except Exception as e:
        print(f"✗ List failed: {e}")
        return []

if __name__ == "__main__":
    # Get bucket name from .env
    bucket = os.getenv("FOOTAGE_BUCKET")
    
    if not bucket:
        print("✗ FOOTAGE_BUCKET not found in .env file")
        print("Run the bucket creation commands first!")
        exit(1)
    
    # Upload test video
    test_video = "C:/cctv-analysis/data/test_video.mp4"
    
    if os.path.exists(test_video):
        upload_video_to_s3(test_video, bucket, camera_id="camera-01")
        list_s3_videos(bucket)
    else:
        print(f"✗ Test video not found: {test_video}")