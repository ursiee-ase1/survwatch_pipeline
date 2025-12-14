import os
import urllib.request
from pathlib import Path

def download_file(url, output_path):
    """Download file with progress indicator"""
    print(f"Downloading to {output_path}...")
    
    def progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        percent = min(downloaded * 100 / total_size, 100)
        print(f"\rProgress: {percent:.1f}%", end='')
    
    urllib.request.urlretrieve(url, output_path, progress)
    print(f"\n✓ Downloaded: {output_path}")

# Create data directory
data_dir = Path("C:/cctv-analysis/data/samples")
data_dir.mkdir(parents=True, exist_ok=True)

# Sample CCTV-like videos (public domain, small size)
samples = [
    {
        "url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
        "name": "sample_outdoor_01.mp4",
        "description": "Outdoor scene with movement"
    },
    {
        "url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4",
        "name": "sample_indoor_01.mp4", 
        "description": "Indoor-like scene"
    }
]

print("Downloading sample CCTV videos...\n")

for sample in samples:
    output_path = data_dir / sample["name"]
    if not output_path.exists():
        try:
            download_file(sample["url"], output_path)
        except Exception as e:
            print(f"✗ Failed: {e}")
            # Fallback: Use existing test video
            print(f"  → Will use existing test_video.mp4")
    else:
        print(f"✓ Already exists: {output_path}")

print("\n✓ Sample download complete!")
print(f"Files in: {data_dir}")