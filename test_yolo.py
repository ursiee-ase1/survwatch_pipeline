"""
Week 1 Sanity Check: Test YOLOv8 on a single video frame
Run time: ~30 seconds (first run downloads model weights)
"""
import cv2
from ultralytics import YOLO
from pathlib import Path

def test_yolo_detection():
    print("🚀 CCTV Analysis - Week 1 Sanity Check")
    print("=" * 50)
    
    # Load YOLOv8 nano model (smallest, fastest for testing)
    print("\n1. Loading YOLOv8n model...")
    model = YOLO('yolov8n.pt')  # Auto-downloads on first run (~6MB)
    print("✅ Model loaded")
    
    # Load video
    video_path = Path("data/test_video.mp4")
    if not video_path.exists():
        print(f"❌ Video not found at {video_path}")
        print("Please download a test video first!")
        return False
    
    print(f"\n2. Opening video: {video_path}")
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        print("❌ Failed to open video")
        return False
    
    # Read first frame
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("❌ Failed to read frame")
        return False
    
    print(f"✅ Frame loaded: {frame.shape[1]}x{frame.shape[0]} pixels")
    
    # Run detection
    print("\n3. Running YOLOv8 detection...")
    results = model(frame, verbose=False)
    
    # Parse results
    detections = results[0].boxes
    print(f"✅ Detection complete: {len(detections)} objects found")
    
    # Display detected objects
    if len(detections) > 0:
        print("\n📦 Detected objects:")
        for i, box in enumerate(detections):
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            class_name = model.names[cls_id]
            print(f"  {i+1}. {class_name} (confidence: {conf:.2%})")
    else:
        print("\n📦 No objects detected (this is OK for testing)")
    
    # Save annotated frame
    output_path = Path("data/test_detection_output.jpg")
    annotated_frame = results[0].plot()
    cv2.imwrite(str(output_path), annotated_frame)
    print(f"\n💾 Saved annotated frame to: {output_path}")
    
    print("\n" + "=" * 50)
    print("✅ Week 1 sanity check PASSED!")
    print("   Your environment is ready for CCTV analysis.")
    return True

if __name__ == "__main__":
    success = test_yolo_detection()
    if not success:
        print("\n⚠️  Check the errors above and try again.")
        exit(1)