# GeoJourney

GeoJourney is a toolkit for organizing, deduplicating, and generating multimedia slideshows from photo and video collections. It is designed for travelers, photographers, and anyone who wants to manage large volumes of media files with geolocation metadata.

## Features
- **Photo and Video Organization:**
  - Organizes photos and videos by date and metadata.
  - Removes or groups duplicates based on file hash and content.
  - Supports EXIF and QuickTime metadata extraction.
- **Slideshow Generation:**
  - Creates travel slideshow videos with maps and narration.
  - Integrates GPS data to generate map overlays.
- **Duplicate Finder:**
  - Recursively scans folders for duplicate files (by hash and size), keeping the oldest and moving others to a specified folder.

## Main Modules
- `organize.py` — Entry point for organizing photos and videos in batch.
- `photo_organizer.py` — Logic for scanning, hashing, and sorting photos.
- `video_organizer.py` — Logic for scanning, hashing, and sorting videos.
- `remove_duplicates.py` — Standalone script for finding and moving duplicate files by hash.
- `main.py` — Generates slideshows with geolocation and narration.

## Directory Structure
```
GeoJourney/
├── analysis/
│   └── map_generator.py
├── assets/
├── composer/
│   └── slideshow_creator.py
├── ingest/
│   ├── media_importer.py
│   └── metadata_extractor.py
├── narration/
│   ├── script_generator.py
│   └── tts_engine.py
├── tests/
├── utils/
│   ├── file_utils.py
│   └── geo_utils.py
├── organize.py
├── photo_organizer.py
├── video_organizer.py
├── remove_duplicates.py
├── main.py
├── requirements.txt
└── README.md
```

## Installation
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd GeoJourney
   ```
2. Install dependencies (recommended: use a virtual environment):
   ```bash
   pip install -r requirements.txt
   ```

## Usage
### Organize Photos and Videos
Run the organizer to scan and sort your media files:
```bash
python organize.py
```
You can adjust input/output folders by editing `organize.py` or passing arguments if implemented.

### Remove Duplicates
Find and move duplicate files (by hash and size):
```bash
python remove_duplicates.py [<folder> [<duplicates_folder>]]
```
- If no arguments are provided, defaults are:
  - Folder: `/srv/i7/.tx/out`
  - Duplicates: `/srv/i7/.tx/duplicate`
- Only the oldest file (by timestamp in filename) is kept; others are moved to `<duplicates_folder>/<hash>/`.

### Generate Slideshow
Create a travel slideshow video with maps and narration:
```bash
python main.py -i <input_folder> -o <output_folder> -r <resolution>
```

## Dependencies
- Python 3.8+
- See `requirements.txt` for all Python dependencies (Pillow, moviepy, exiftool-wrapper, tqdm, etc.)
- [ExifTool](https://exiftool.org/) must be installed on your system for metadata extraction.

## Credits
Developed by Munif Gebara and contributors.

## License
MIT License