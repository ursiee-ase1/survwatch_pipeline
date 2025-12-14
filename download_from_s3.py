import boto3
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("C:/cctv-analysis/.env")

def download_video_from_s3(bucket_name, s3_key, output_path):
    """
    Download video from S3
    
    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key (path in bucket)
        output_path: Local path to save video
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    s3 = boto3.client('s3', region_name='us-east-1')
    
    print(f"\n{'='*60}")
    print(f"Downloading from S3...")
    print(f"Bucket: {bucket_name}")
    print(f"Key: {s3_key}")
    print(f"{'='*60}\n")
    
    try:
        # Get object metadata first
        metadata = s3.head_object(Bucket=bucket_name, Key=s3_key)
        size_mb = metadata['ContentLength'] / 1024 / 1024
        
        print(f"File size: {size_mb:.2f} MB")
        print(f"Downloading to: {output_path}\n")
        
        # Download file
        s3.download_file(bucket_name, s3_key, str(output_path))
        
        print(f"✓ Download successful!")
        print(f"Saved to: {output_path}")
        
        return str(output_path)
        
    except s3.exceptions.NoSuchKey:
        print(f"✗ File not found in S3: {s3_key}")
        raise
    except Exception as e:
        print(f"✗ Download failed: {e}")
        raise

def download_latest_video(bucket_name, camera_id, output_dir):
    """Download most recent video for a camera"""
    s3 = boto3.client('s3', region_name='us-east-1')
    
    prefix = f"{camera_id}/"
    
    try:
        response = s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            print(f"No videos found for {camera_id}")
            return None
        
        # Sort by last modified, get most recent
        latest = sorted(response['Contents'], key=lambda x: x['LastModified'])[-1]
        s3_key = latest['Key']
        
        # Extract filename
        filename = Path(s3_key).name
        output_path = Path(output_dir) / filename
        
        print(f"Latest video: {s3_key}")
        return download_video_from_s3(bucket_name, s3_key, output_path)
        
    except Exception as e:
        print(f"✗ Failed to find latest video: {e}")
        return None

if __name__ == "__main__":
    bucket = os.getenv("FOOTAGE_BUCKET")
    
    if not bucket:
        print("✗ FOOTAGE_BUCKET not found in .env")
        exit(1)
    
    # Download specific file
    s3_key = "camera-01/2024-01-01/test_video.mp4"  # Modify with actual key
    output = "C:/cctv-analysis/data/downloaded"
    
    print("To download, update the s3_key variable with actual S3 path")
    print(f"Current s3_key: {s3_key}")
    
    # Or download latest
    # download_latest_video(bucket, "camera-01", output)