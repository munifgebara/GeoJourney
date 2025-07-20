from photo_organizer import organize_photos
from video_organizer import organize_videos
import sys


def main():
    DEFAULT_INPUT = "/media/munif/MunifTx2025/.tx/in"
    DEFAULT_OUTPUT = "/media/munif/MunifTx2025/.tx/out"

    if len(sys.argv) == 3:
        input_folder = sys.argv[1]
        output_folder = sys.argv[2]
    else:
        print(f"[INFO] Using default folders: {DEFAULT_INPUT} -> {DEFAULT_OUTPUT}")
        input_folder = DEFAULT_INPUT
        output_folder = DEFAULT_OUTPUT

   
    print("--- Organizing VIDEOS ---")
    organize_videos(input_folder, output_folder)

    print("--- Organizing PHOTOS ---")
    organize_photos(input_folder, output_folder)
   

if __name__ == "__main__":
    main()
