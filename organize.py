from pathlib import Path
from photo_organizer import organize_photos
import remove_duplicates
from video_organizer import organize_videos
import sys


def main():
    DEFAULT_INPUT = "/srv/i7/q/q"
    DEFAULT_OUTPUT = "/srv/i7/.tx/out"

    if len(sys.argv) == 3:
        input_folder = sys.argv[1]
        output_folder = sys.argv[2]
    else:
        print(f"[INFO] Using default folders: {DEFAULT_INPUT} -> {DEFAULT_OUTPUT}")
        input_folder = DEFAULT_INPUT
        output_folder = DEFAULT_OUTPUT

   

    print("--- Organizing PHOTOS ---")
    organize_photos(input_folder, output_folder)

    print("--- Organizing VIDEOS ---")
    organize_videos(input_folder, output_folder)
    

    remove_duplicates.remove_duplicate_files(output_folder, str(Path(output_folder).parent)+"/duplicate")

   

if __name__ == "__main__":
    main()
