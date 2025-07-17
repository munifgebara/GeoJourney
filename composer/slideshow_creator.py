from pathlib import Path
from moviepy.editor import ImageClip, VideoFileClip, concatenate_videoclips

def create_slideshow(media_files: list[Path], output_path: Path, resolution: str = "1280x720", image_duration: int = 5):
    width, height = map(int, resolution.split("x"))
    clips = []

    for f in media_files:
        ext = f.suffix.lower()

        if ext in ['.jpg', '.jpeg', '.png', '.heic']:
            img = ImageClip(str(f)).set_duration(image_duration)
            img = img.resize(height=height)
            clips.append(img)

        elif ext in ['.mp4', '.mov', '.mkv']:
            video = VideoFileClip(str(f)).resize(height=height)
            clips.append(video)

    if not clips:
        print("No media to compose.")
        return

    final_clip = concatenate_videoclips(clips, method="compose")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_clip.write_videofile(str(output_path), fps=24)
