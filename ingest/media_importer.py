from pathlib import Path
from typing import List
from exiftool import ExifToolHelper
from tqdm import tqdm

SUPPORTED_EXTENSIONS = {'.heic', '.jpg', '.jpeg', '.mov', '.mp4'}

def list_media_with_gps(input_dir: Path) -> List[Path]:
    """
    Returns a list of media files that contain GPS metadata.
    Progress is shown as each file is processed.
    """
    files_with_gps = []
    all_files = [f for f in input_dir.rglob("*") if f.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not all_files:
        return []

    with ExifToolHelper() as et:
        for f in tqdm(all_files, desc="Reading metadata"):
            metadata = et.get_metadata(str(f))
            if not metadata:
                continue

            item = metadata[0]
            source_file = item.get("SourceFile")
            gps_lat = item.get("EXIF:GPSLatitude") or item.get("QuickTime:GPSLatitude")
            gps_lon = item.get("EXIF:GPSLongitude") or item.get("QuickTime:GPSLongitude")

            if gps_lat and gps_lon and source_file:
                files_with_gps.append(Path(source_file))

    return files_with_gps
