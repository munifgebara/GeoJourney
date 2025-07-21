# remove_duplicates.py
"""
Remove duplicate files in a folder recursively, based on the hash in the filename, ignoring the timestamp.
Keeps the oldest file (smallest date) and moves the most recent ones to duplicated/<hash>/
"""

import os
import shutil
from pathlib import Path
from datetime import datetime


def extract_hash_from_filename(filename):
    """
    Extracts the hash from the filename, assuming format: <timestamp>_<hash>.<ext> or <timestamp>-<hash>.<ext>
    """
    name = Path(filename).stem
    if '_' in name:
        parts = name.split('_', 1)
    elif '-' in name:
        parts = name.split('-', 1)
    else:
        parts = [name]
    if len(parts) == 2:
        return parts[1]
    return None

def extract_timestamp_from_filename(filename):
    """
    Extracts the timestamp from the filename, assuming format: <timestamp>_<hash>.<ext> or <timestamp>-<hash>.<ext>
    """
    name = Path(filename).stem
    if '_' in name:
        parts = name.split('_', 1)
    elif '-' in name:
        parts = name.split('-', 1)
    else:
        parts = [name]
    if len(parts) == 2:
        return parts[0]
    return None

def remove_duplicate_files(root_folder, duplicated_folder):
    """
    Recursively scans root_folder, finds files with the same hash (in the name) and size,
    keeps the oldest (smallest timestamp) and moves the others to <duplicated_folder>/<hash>/
    """
    print(f"[START] Recursive scan in: {root_folder}")
    files_by_hash = {}
    root = Path(root_folder)
    duplicated_base = Path(duplicated_folder)
    all_files = list(root.rglob('*'))
    file_count = 0
    for file in all_files:
        if file.is_file():
            file_count += 1
            hash_part = extract_hash_from_filename(file.name)
            timestamp = extract_timestamp_from_filename(file.name)
            if not hash_part or not timestamp:
                continue
            size = file.stat().st_size
            key = (hash_part, size)
            files_by_hash.setdefault(key, []).append((file, timestamp))
    print(f"[INFO] {file_count} files found.")
    print(f"[INFO] {len(files_by_hash)} groups (hash+size) identified.")

    duplicated_groups = 0
    total_moved = 0
    total_kept = 0
    for (hash_part, size), files in files_by_hash.items():
        if len(files) <= 1:
            continue
        duplicated_groups += 1
        print(f"\n[GROUP] Hash: {hash_part} | Size: {size} bytes | {len(files)} files")
        # Sort by timestamp (smallest = oldest)
        files_sorted = sorted(files, key=lambda x: x[1])
        # Keep the oldest
        to_keep = files_sorted[0][0]
        to_move = [f[0] for f in files_sorted[1:]]
        duplicated_dir = duplicated_base / hash_part
        duplicated_dir.mkdir(parents=True, exist_ok=True)
        for f in to_move:
            target = duplicated_dir / f.name
            print(f"  [MOVE] {f} -> {target}")
            shutil.move(str(f), str(target))
            total_moved += 1
        print(f"  [KEEP] {to_keep}")
        total_kept += 1
    print(f"\n[SUMMARY] {duplicated_groups} duplicate groups processed.")
    print(f"[SUMMARY] {total_kept} files kept, {total_moved} files moved to {duplicated_base}/<hash>/.")
    print("[FINISHED] Operation completed.")

if __name__ == "__main__":
    import sys
    DEFAULT_ROOT = "/mnt/7937a629-8811-4af0-ae7a-097a78cc4d2c/bkpSansung/out"
    DEFAULT_DUPLICATES = "/mnt/7937a629-8811-4af0-ae7a-097a78cc4d2c/bkpSansung/duplicate"

    if len(sys.argv) == 1:
        print(f"[INFO] Using defaults: folder={DEFAULT_ROOT}, duplicates={DEFAULT_DUPLICATES}")
        remove_duplicate_files(DEFAULT_ROOT, DEFAULT_DUPLICATES)
    elif len(sys.argv) == 2:
        print(f"[INFO] Using folder={sys.argv[1]}, duplicates={DEFAULT_DUPLICATES}")
        remove_duplicate_files(sys.argv[1], DEFAULT_DUPLICATES)
    elif len(sys.argv) == 3:
        remove_duplicate_files(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python remove_duplicates.py [<folder> [<duplicates_folder>]]")
