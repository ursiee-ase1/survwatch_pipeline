"""
extract_clips.py - Extract video clips for detected threats
Extracts 30-second clips centered on threat detection timestamp
"""

import cv2
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any


def extract_threat_clips(video_path: Path,
                        threats: List[Dict[str, Any]],
                        output_dir: Path,
                        clip_duration: int = 30,
                        use_ffmpeg: bool = True) -> List[Path]:
    """
    Extract video clips for detected threats
    
    Args:
        video_path: Path to source video
        threats: List of threat dictionaries with timestamps
        output_dir: Directory to save clips
        clip_duration: Duration of each clip in seconds
        use_ffmpeg: Use ffmpeg (faster) vs OpenCV
        
    Returns:
        List of paths to extracted clips
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    if not threats:
        print("No threats to extract clips for")
        return []
    
    # Get video FPS for timestamp calculations
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    cap.release()
    
    print(f"📹 Extracting clips from: {video_path.name}")
    print(f"   Video duration: {duration:.1f}s, FPS: {fps:.1f}")
    print(f"   Threats to extract: {len(threats)}")
    
    extracted_clips = []
    
    # Group nearby threats to avoid duplicate clips
    threat_groups = group_nearby_threats(threats, window_seconds=clip_duration)
    
    print(f"   Grouped into {len(threat_groups)} unique clips")
    
    for idx, threat_group in enumerate(threat_groups, 1):
        # Use first threat in group for naming
        primary_threat = threat_group[0]
        frame_number = primary_threat['frame_number']
        threat_level = primary_threat['threat_level']
        detected_class = primary_threat['detected_class']
        
        # Parse timestamp
        if isinstance(primary_threat['timestamp'], str):
            timestamp = datetime.fromisoformat(primary_threat['timestamp'])
        else:
            timestamp = primary_threat['timestamp']
        
        # Calculate clip start time (center the threat)
        start_frame = max(0, frame_number - int(clip_duration * fps / 2))
        start_time = start_frame / fps
        
        # Clip filename
        time_str = timestamp.strftime('%H%M%S')
        clip_filename = f"{threat_level}_{detected_class}_{time_str}_frame{frame_number}.mp4"
        clip_path = output_dir / clip_filename
        
        # Extract clip
        if use_ffmpeg and check_ffmpeg_available():
            success = extract_with_ffmpeg(
                video_path, clip_path, start_time, clip_duration
            )
        else:
            success = extract_with_opencv(
                video_path, clip_path, start_frame, int(clip_duration * fps), fps
            )
        
        if success:
            extracted_clips.append(clip_path)
            print(f"   ✅ [{idx}/{len(threat_groups)}] {clip_filename}")
        else:
            print(f"   ❌ [{idx}/{len(threat_groups)}] Failed: {clip_filename}")
    
    print(f"✅ Extracted {len(extracted_clips)} clips to: {output_dir}")
    return extracted_clips


def group_nearby_threats(threats: List[Dict[str, Any]], 
                        window_seconds: int = 30) -> List[List[Dict[str, Any]]]:
    """
    Group threats that occur within window_seconds of each other
    to avoid extracting overlapping clips
    """
    if not threats:
        return []
    
    # Sort by frame number
    sorted_threats = sorted(threats, key=lambda t: t['frame_number'])
    
    groups = []
    current_group = [sorted_threats[0]]
    
    for threat in sorted_threats[1:]:
        # If threat is within window of last threat in group, add to group
        frame_diff = threat['frame_number'] - current_group[-1]['frame_number']
        
        # Assume 30 FPS for rough calculation (actual FPS used later)
        time_diff_seconds = frame_diff / 30.0
        
        if time_diff_seconds <= window_seconds:
            current_group.append(threat)
        else:
            groups.append(current_group)
            current_group = [threat]
    
    # Add last group
    if current_group:
        groups.append(current_group)
    
    return groups


def check_ffmpeg_available() -> bool:
    """Check if ffmpeg is available"""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      capture_output=True, 
                      check=True,
                      timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def extract_with_ffmpeg(video_path: Path,
                       output_path: Path,
                       start_time: float,
                       duration: int) -> bool:
    """
    Extract clip using ffmpeg (fast, recommended)
    
    Args:
        video_path: Source video
        output_path: Output clip path
        start_time: Start time in seconds
        duration: Clip duration in seconds
    """
    try:
        cmd = [
            'ffmpeg',
            '-ss', str(start_time),  # Start time
            '-i', str(video_path),    # Input file
            '-t', str(duration),      # Duration
            '-c', 'copy',             # Copy codec (fast)
            '-y',                     # Overwrite output
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"      ffmpeg error: {e}")
        return False


def extract_with_opencv(video_path: Path,
                       output_path: Path,
                       start_frame: int,
                       frame_count: int,
                       fps: float) -> bool:
    """
    Extract clip using OpenCV (slower fallback)
    
    Args:
        video_path: Source video
        output_path: Output clip path
        start_frame: Starting frame number
        frame_count: Number of frames to extract
        fps: Video FPS
    """
    try:
        cap = cv2.VideoCapture(str(video_path))
        
        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        # Seek to start frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        # Write frames
        for _ in range(frame_count):
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
        
        cap.release()
        out.release()
        
        return output_path.exists()
        
    except Exception as e:
        print(f"      OpenCV error: {e}")
        return False


def main():
    """Test clip extraction"""
    from datetime import datetime
    
    # Test configuration
    video_path = Path('data/samples/test_video.mp4')
    output_dir = Path('data/test_clips')
    
    # Sample threats
    sample_threats = [
        {
            'frame_number': 500,
            'timestamp': datetime(2025, 1, 15, 23, 30, 15),
            'threat_level': 'HIGH',
            'detected_class': 'person',
            'alert': True
        },
        {
            'frame_number': 1200,
            'timestamp': datetime(2025, 1, 15, 23, 31, 45),
            'threat_level': 'MEDIUM',
            'detected_class': 'car',
            'alert': True
        }
    ]
    
    if not video_path.exists():
        print(f"❌ Test video not found: {video_path}")
        return
    
    print("=== Clip Extraction Test ===")
    print(f"FFmpeg available: {check_ffmpeg_available()}")
    
    clips = extract_threat_clips(
        video_path=video_path,
        threats=sample_threats,
        output_dir=output_dir,
        clip_duration=30
    )
    
    print(f"\n✅ Test complete! Extracted {len(clips)} clips to {output_dir}")


if __name__ == '__main__':
    main()