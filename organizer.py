import os
from pathlib import Path
import shutil
from PIL import Image
import imagehash
import exiftool
from datetime import datetime
import pillow_heif
pillow_heif.register_heif_opener()

SUPPORTED_EXTENSIONS = {
    '.jpg', '.jpeg', '.heic', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.avif', '.jfif',
    '.ppm', '.pnm', '.pbm', '.pgm', '.tga', '.ico', '.ras'
}

def generate_image_hash(image_path):
    try:
        with Image.open(image_path) as img:
            img_hash = imagehash.phash(img.resize((256, 256)).convert("L"))
            return str(img_hash)
    except Exception as e:
        print(f"[ERROR] Failed to generate hash for {image_path}: {e}")
        return None

def extract_date(metadata):
    """
    Extrai datetime e milissegundos dos metadados EXIF.
    Retorna (datetime_obj, milissegundos:int) ou (None, 0) se não encontrar.
    """
    for field in ['EXIF:DateTimeOriginal', 'EXIF:CreateDate']:
        if field in metadata:
            try:
                dt = datetime.strptime(metadata[field], "%Y:%m:%d %H:%M:%S")
                # Procurar subsegundos
                subsec = None
                for subsec_field in [
                    'EXIF:SubSecTimeOriginal',
                    'EXIF:SubSecTimeDigitized',
                    'EXIF:SubSecTime']:
                    if subsec_field in metadata:
                        subsec = metadata[subsec_field]
                        break
                try:
                    ms = int(str(subsec).ljust(3, '0')[:3]) if subsec is not None else 0
                except Exception:
                    ms = 0
                return dt, ms
            except ValueError:
                continue
    return None, 0

def organize_photos(source_folder, output_folder):
    source = Path(source_folder)
    output = Path(output_folder)

    print(f"[START] Scanning folder: {source}")
    files = list(source.rglob('*'))
    total_files = len(files)
    print(f"[INFO] {total_files} total files found.\n")

    analyzed = 0
    moved = 0
    replaced = 0
    removed_src = 0
    skipped_no_exif = 0
    skipped_no_hash = 0
    skipped_duplicate = 0
    skipped_metadata_error = 0
    skipped_unexpected_error = 0

    import json
    import sys
    from datetime import datetime as dt
    import os

    with exiftool.ExifTool() as et:
        for idx, file_path in enumerate(files, start=1):
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            print(f"[{idx}/{total_files}] Analyzing: {file_path.name}")
            analyzed += 1
            try:
                try:
                    metadata_bytes = et.execute('-j', str(file_path))  # '-j' outputs JSON
                    metadata_list = json.loads(metadata_bytes)
                    metadata = metadata_list[0] if metadata_list else {}
                except Exception as e:
                    msg = f"  [ERROR] Could not read metadata: {e}"
                    print(msg)
                    skipped_metadata_error += 1
                    continue

                photo_date, ms = extract_date(metadata)
                used_exif = True
                if not photo_date:
                    # Tenta data de modificação do arquivo
                    stat = file_path.stat()
                    dt_file = datetime.fromtimestamp(stat.st_mtime)
                    ms = int((stat.st_mtime - int(stat.st_mtime)) * 1000)
                    photo_date = dt_file
                    used_exif = False

                image_hash = generate_image_hash(file_path)
                if not image_hash:
                    msg = f"  [SKIPPED] Could not generate hash."
                    print(msg)
                    # Move para pasta errors
                    errors_folder = output / "errors"
                    errors_folder.mkdir(parents=True, exist_ok=True)
                    error_target = errors_folder / file_path.name
                    try:
                        shutil.move(str(file_path), str(error_target))
                        print(f"  [MOVED TO ERRORS] {file_path} -> {error_target}")
                    except Exception as e:
                        print(f"  [ERROR] Could not move to errors: {e}")
                    skipped_no_hash += 1
                    continue

                if used_exif:
                    target_folder = output / "date"/str(photo_date.year) / f"{photo_date.month:02d}" / f"{photo_date.day:02d}"
                else:
                    target_folder = output / "no-date" / str(photo_date.year) / f"{photo_date.month:02d}" / f"{photo_date.day:02d}"
                target_folder.mkdir(parents=True, exist_ok=True)

                ext = file_path.suffix.lower()
                timestamp_s = int(photo_date.timestamp())
                target_file = target_folder / f"{timestamp_s}{ms:03d}-{image_hash}{ext}"

                if not target_file.exists():
                    shutil.move(str(file_path), str(target_file))
                    moved += 1
                    msg = f"  [MOVED{' - NO EXIF' if not used_exif else ''}] {file_path} -> {target_file}"
                    print(msg)
                else:
                    # Arquivo já existe, comparar tamanhos
                    src_size = file_path.stat().st_size
                    dst_size = target_file.stat().st_size
                    if src_size > dst_size:
                        target_file.unlink()
                        shutil.move(str(file_path), str(target_file))
                        replaced += 1
                        msg = f"  [REPLACED] {file_path} (larger) replaced and moved to: {target_file}"
                        print(msg)
                    elif src_size < dst_size:
                        file_path.unlink()
                        removed_src += 1
                        msg = f"  [REMOVED] {file_path} (smaller) removed, kept destination: {target_file}"
                        print(msg)
                    elif src_size == dst_size:
                        file_path.unlink()
                        removed_src += 1
                        msg = f"  [REMOVED] {file_path} (duplicate same size), kept destination: {target_file}"
                        print(msg)
                    else:
                        msg = f"  [DUPLICATE] Already exists."
                        skipped_duplicate += 1
                        print(msg)

                if not used_exif:
                    skipped_no_exif += 1
            except Exception as e:
                msg = f"  [ERROR] Unexpected error processing {file_path}: {e}"
                print(msg)
                skipped_unexpected_error += 1
                continue

    print("\n[FINISHED]")
    print(f"Total analyzed files: {analyzed}")
    print(f"Total moved:          {moved}")
    print(f"Total replaced:       {replaced}")
    print(f"Total removed src:    {removed_src}")
    print(f"Total skipped (no EXIF date):   {skipped_no_exif}")
    print(f"Total skipped (could not generate hash): {skipped_no_hash}")
    print(f"Total skipped (duplicate - not handled): {skipped_duplicate}")
    print(f"Total skipped (metadata error): {skipped_metadata_error}")
    print(f"Total skipped (unexpected error): {skipped_unexpected_error}")

# Example usage:


organize_photos("/srv/i7/.tx/in", "/srv/i7/.tx/out")



