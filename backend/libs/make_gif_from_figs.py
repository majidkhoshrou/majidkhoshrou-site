from PIL import Image, ImageOps
from pathlib import Path

def make_gif_from_dir(path: Path, output_gif: str = "animated_output.gif", duration: int = 1000):
    path = Path(path)

    # Get all PNG files, sorted
    image_paths = sorted([p for p in path.iterdir() if p.suffix.lower() == ".png"])
    if not image_paths:
        raise FileNotFoundError("No PNG files found in the specified directory.")

    # Open and convert all images
    images = [Image.open(p).convert("RGB") for p in image_paths]

    # Determine max dimensions
    max_width = max(img.width for img in images)
    max_height = max(img.height for img in images)

    # Resize and pad each image to the same canvas size
    def pad_image(img):
        return ImageOps.pad(img, (max_width, max_height), color=(255, 255, 255))

    padded_images = [pad_image(img) for img in images]

    # Save GIF
    gif_path = path / output_gif
    padded_images[0].save(gif_path, save_all=True, append_images=padded_images[1:], duration=duration, loop=0)

    print(f"GIF saved at: {gif_path}")

# Usage
make_gif_from_dir('/mnt/c/Users/al27278/OneDrive - Alliander NV/Output/create_gif/forecasting')
