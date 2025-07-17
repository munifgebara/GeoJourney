from pathlib import Path
from moviepy.editor import ImageClip, VideoFileClip, concatenate_videoclips, CompositeVideoClip
from tqdm import tqdm
from utils.geo_utils import extract_gps_from_image
from analysis.map_generator import generate_map_image
from pathlib import Path
import tempfile

def create_slideshow(media_files: list[Path], output_path: Path, resolution: str = "1280x720", image_duration: int = 5, skip_n: int = 5):
    width, height = map(int, resolution.split("x"))
    clips = []

    # Ordena pelas datas do EXIF (ou usa mtime se não houver)
    def get_timestamp(f):
        try:
            from exiftool import ExifToolHelper
            with ExifToolHelper() as et:
                metadata = et.get_metadata(str(f))
                if metadata and 'EXIF:DateTimeOriginal' in metadata[0]:
                    from datetime import datetime
                    return datetime.strptime(metadata[0]['EXIF:DateTimeOriginal'], '%Y:%m:%d %H:%M:%S').timestamp()
        except Exception:
            pass
        return f.stat().st_mtime
    from tqdm import tqdm
    timestamps = []
    for f in tqdm(media_files, desc="Ordenando por data EXIF"):
        timestamps.append((f, get_timestamp(f)))
    media_files = [f for f, _ in sorted(timestamps, key=lambda x: x[1])]

    # Pula de skip_n em skip_n
    media_files = media_files[::skip_n]

    for f in tqdm(media_files, desc="Processando arquivos"):
        ext = f.suffix.lower()

        if ext in ['.jpg', '.jpeg', '.png', '.heic']:
            img = ImageClip(str(f)).set_duration(image_duration)
            img = img.resize(height=height)
            gps = extract_gps_from_image(f)
            if gps:
                lat, lon = gps
                with tempfile.TemporaryDirectory() as tmpdir:
                    map_path = Path(tmpdir) / (f.stem + '_map.png')
                    generate_map_image(lat, lon, map_path, size=(200, 200))
                    map_clip = ImageClip(str(map_path)).set_duration(image_duration)
                    # Coloca o mapa no canto inferior direito
                    map_clip = map_clip.set_position((img.w - 210, img.h - 210))  # 10px padding
                    img = CompositeVideoClip([img, map_clip], size=(img.w, img.h))
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
