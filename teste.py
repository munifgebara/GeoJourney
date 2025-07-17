import exiftool

files = ["/home/munif/Pictures/viagem/Photos-1-001/IMG_8543.HEIC"]
with exiftool.ExifToolHelper() as et:
    metadata = et.get_metadata(files)
    for d in metadata:
        print("{:20.20} {:20.20}".format(d["SourceFile"],
                                         d["EXIF:DateTimeOriginal"]))