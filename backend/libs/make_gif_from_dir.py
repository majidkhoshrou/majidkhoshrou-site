from pathlib import Path
from PIL import Image, ImageOps
import cv2
import numpy as np

def extract_frames_from_video(video_path: Path, output_dir: Path, num_frames: int = 15):
    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_indices = [int(i) for i in 
                     list(np.linspace(0, total_frames - 1, num_frames))]
    
    extracted_paths = []
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        success, frame = cap.read()
        if not success:
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        frame_path = output_dir / f"{video_path.stem}_frame_{idx:04d}.png"
        img.save(frame_path)
        extracted_paths.append(frame_path)
    cap.release()
    return extracted_paths

def make_gif_from_dir(path: Path, output_gif: str = "animated_output.gif", duration: int = 1000):
    import numpy as np  # Needed for linspace in frame extraction
    path = Path(path)
    output_dir = path / "extracted_frames"
    output_dir.mkdir(exist_ok=True)

    image_paths = []

    # Handle MP4 files by extracting frames
    for video_file in path.glob("*.mp4"):
        print(f"Extracting frames from: {video_file.name}")
        image_paths.extend(extract_frames_from_video(video_file, output_dir))

    # Also collect existing PNGs
    image_paths.extend(sorted([p for p in path.glob("*.png")]))

    if not image_paths:
        raise FileNotFoundError("No MP4 or PNG files found in the specified directory.")

    # Open and convert all images
    images = [Image.open(p).convert("RGB") for p in image_paths]

    # Determine max canvas size
    max_width = max(img.width for img in images)
    max_height = max(img.height for img in images)

    # Resize and pad
    def pad_image(img):
        return ImageOps.pad(
            img,
            (max_width, max_height),
            method=Image.Resampling.LANCZOS,  # or Image.ANTIALIAS for older PIL
            color=(255, 255, 255),
            centering=(0.5, 0.5)
        )

    padded_images = [pad_image(img) for img in images]

    # Save GIF
    gif_path = path / output_gif
    padded_images[0].save(gif_path, save_all=True, append_images=padded_images[1:], duration=duration, loop=0)
    print(f"GIF saved at: {gif_path}")

# Usage example
make_gif_from_dir(Path('/mnt/c/Users/al27278/OneDrive - Alliander NV/Output/create_gif/gmm'))