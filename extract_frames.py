import cv2
import os
from pathlib import Path
from datetime import datetime

def extract_frames(video_path, output_dir, fps=1, max_frames=None):
    """
    Extract frames from video at specified FPS
    
    Args:
        video_path: Path to input video
        output_dir: Directory to save frames
        fps: Frames per second to extract (default: 1)
        max_frames: Maximum frames to extract (None = all)
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
    print(f"Video: {video_path.name}")
    print(f"Original FPS: {video_fps:.2f}")
    print(f"Duration: {duration:.2f}s")
    print(f"Total frames: {total_frames}")
    print(f"Extracting at: {fps} fps")
    print(f"{'='*60}\n")
    
    # Calculate frame skip interval
    frame_skip = int(video_fps / fps)
    
    frame_count = 0
    extracted_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Extract frame at specified interval
        if frame_count % frame_skip == 0:
            # Generate filename with timestamp
            timestamp = frame_count / video_fps
            filename = f"frame_{extracted_count:04d}_t{timestamp:.2f}s.jpg"
            output_path = output_dir / filename
            
            # Save frame
            cv2.imwrite(str(output_path), frame)
            extracted_count += 1
            
            print(f"✓ Extracted: {filename} (frame {frame_count}/{total_frames})")
            
            # Check max frames limit
            if max_frames and extracted_count >= max_frames:
                print(f"\n⚠ Reached max_frames limit: {max_frames}")
                break
        
        frame_count += 1
    
    cap.release()
    
    print(f"\n{'='*60}")
    print(f"✓ Extraction complete!")
    print(f"Total extracted: {extracted_count} frames")
    print(f"Saved to: {output_dir}")
    print(f"{'='*60}\n")
    
    return extracted_count

if __name__ == "__main__":
    # Test with existing video
    video = "C:/cctv-analysis/data/test_video.mp4"
    output = "C:/cctv-analysis/data/frames"
    
    if os.path.exists(video):
        extract_frames(video, output, fps=1, max_frames=10)
    else:
        print(f"✗ Video not found: {video}")
        print("Place a video at the path above or modify the path")