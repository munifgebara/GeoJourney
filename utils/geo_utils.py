# geo_utils.py
from typing import Optional, Tuple
from pathlib import Path
from exiftool import ExifToolHelper

def extract_gps_from_image(image_path: Path) -> Optional[Tuple[float, float]]:
    """
    Extrai latitude e longitude de uma imagem (caso existam nos metadados EXIF).
    Retorna (latitude, longitude) como floats, ou None se não houver GPS.
    """
    with ExifToolHelper() as et:
        metadata = et.get_metadata(str(image_path))
        if not metadata:
            return None
        item = metadata[0]
        gps_lat = item.get("EXIF:GPSLatitude") or item.get("QuickTime:GPSLatitude")
        gps_lon = item.get("EXIF:GPSLongitude") or item.get("QuickTime:GPSLongitude")
        if gps_lat and gps_lon:
            try:
                return float(gps_lat), float(gps_lon)
            except Exception:
                pass
    return None