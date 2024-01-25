from PIL import Image, ExifTags
import os


def clean_metadata(image_path, output_directory, counter):
    try:
        img = Image.open(image_path)
        exif = img.getexif()

        tags_to_remove = [ExifTags.TAGS.get(tag, tag) for tag in [271, 272, 305, 306]]

        for tag in tags_to_remove:
            if tag in exif:
                del exif[tag]

        new_filename = f"taiga_{counter}.jpg"
        new_filepath = os.path.join(output_directory, new_filename)

        img.save(new_filepath, exif=img.info["exif"])
        print(f"Metadata cleaned for: {image_path}. Renamed to: {new_filepath}")

        os.remove(image_path)
        print(f"Original file deleted: {image_path}")

    except Exception as e:
        print(f"Error processing {image_path}: {e}")


def main(directory_path, output_directory):
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    counter = 1

    for filename in os.listdir(directory_path):
        if filename.endswith((".jpg", ".jpeg", ".png")):
            image_path = os.path.join(directory_path, filename)
            clean_metadata(image_path, output_directory, counter)
            counter += 1


main("../taiga", "../taiga")
