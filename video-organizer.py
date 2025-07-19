import os
from pathlib import Path
import shutil
import exiftool
from datetime import datetime
from utils.file_utils import generate_file_hash

SUPPORTED_VIDEO_EXTENSIONS = {
    '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.mpeg', '.mpg', '.3gp', '.mts', '.m2ts', '.ts', '.m4v', '.vob', '.ogv', '.rm', '.rmvb'
}

def extract_video_date(metadata):
    """
    Extrai datetime dos metadados de vídeo.
    Retorna (datetime_obj, milissegundos:int) ou (None, 0) se não encontrar.
    """
    for field in ['QuickTime:CreateDate', 'QuickTime:ModifyDate', 'EXIF:CreateDate', 'EXIF:MediaCreateDate', 'EXIF:MediaModifyDate']:
        if field in metadata:
            try:
                dt = datetime.strptime(metadata[field], "%Y:%m:%d %H:%M:%S")
                ms = 0
                return dt, ms
            except ValueError:
                continue
    return None, 0

def organize_videos(source_folder, output_folder):
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
    skipped_metadata_error = 0
    skipped_unexpected_error = 0

    import json
    import sys
    from datetime import datetime as dt
    import os

    with exiftool.ExifTool() as et:
        for idx, file_path in enumerate(files, start=1):
            if file_path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
                continue
            print(f"[{idx}/{total_files}] Analyzing: {file_path.name}")
            analyzed += 1
            try:
                try:
                    metadata_bytes = et.execute('-j', str(file_path))
                    metadata_list = json.loads(metadata_bytes)
                    metadata = metadata_list[0] if metadata_list else {}
                except Exception as e:
                    msg = f"  [ERROR] Could not read metadata: {e}"
                    print(msg)
                    skipped_metadata_error += 1
                    continueg
                video_date, ms = extract_video_date(metadata)
                used_exif = True
                if not video_date:
                    # Tenta data de modificação do arquivo
                    stat = file_path.stat()
                    dt_file = datetime.fromtimestamp(stat.st_mtime)
                    ms = int((stat.st_mtime - int(stat.st_mtime)) * 1000)
                    video_date = dt_file
                    used_exif = False

                # Estrutura: video-date/ano/mes ou video-no-date/ano/mes
                if used_exif:
                    target_folder = output / "video-date" / str(video_date.year) / f"{video_date.month:02d}"
                else:
                    target_folder = output / "video-no-date" / str(video_date.year) / f"{video_date.month:02d}"
                target_folder.mkdir(parents=True, exist_ok=True)

                ext = file_path.suffix.lower()
                timestamp_s = int(video_date.timestamp())
                # Gera hash do arquivo de vídeo
                video_hash = generate_file_hash(file_path)
                target_file = target_folder / f"{timestamp_s}{ms:03d}_{video_hash}{ext}"

                if not target_file.exists():
                    shutil.move(str(file_path), str(target_file))
                    moved += 1
                    msg = f"  [MOVED{' - NO EXIF' if not used_exif else ''}] {file_path} -> {target_file}"
                    print(msg)
                else:
                    # Arquivo já existe com o mesmo hash: duplicata real
                    file_path.unlink()
                    removed_src += 1
                    msg = f"  [REMOVED] {file_path} (duplicate hash), kept destination: {target_file}"
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
    print(f"Total skipped (metadata error): {skipped_metadata_error}")
    print(f"Total skipped (unexpected error): {skipped_unexpected_error}")

# Example usage:

organize_videos("/srv/i7/.tx/in", "/srv/i7/.tx/out")
