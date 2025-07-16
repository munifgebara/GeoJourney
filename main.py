import argparse
from pathlib import Path
from ingest.media_importer import list_media_with_gps  # ajuste o caminho conforme sua estrutura

def parse_args():
    parser = argparse.ArgumentParser(description="GeoJourney - Generate travel slideshow videos with narration and maps.")
    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=Path("/home/munif/Pictures/viagem"),
        help="Path to the input folder containing images and videos"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("/home/munif/Videos"),
        help="Path to the output folder where generated videos will be saved"
    )
    parser.add_argument(
        "-r", "--resolution",
        type=str,
        default="1280x720",  # HD
        help="Resolution of the output video (e.g., 1920x1080, 1280x720)"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    print(f"Input folder: {args.input}")
    print(f"Output folder: {args.output}")
    print(f"Resolution: {args.resolution}")

    media_files = list_media_with_gps(args.input)
    print(f"Found {len(media_files)} media files with GPS data:")
    for f in media_files:
        print(f" - {f}")

if __name__ == "__main__":
    main()
