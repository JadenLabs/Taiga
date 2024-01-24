"""Removes metadata from images in a directory
"""

from PIL import Image


def clean_metadata(image_path):
    try:
        img = Image.open(image_path)
        img.info = {}
        img.save(image_path)
        print(f"Metadata cleaned for: {image_path}")
    except Exception as e:
        print(f"Error processing {image_path}: {e}")


def main(directory_path):
    import os

    for filename in os.listdir(directory_path):
        if filename.endswith((".jpg", ".jpeg", ".png")):
            image_path = os.path.join(directory_path, filename)
            clean_metadata(image_path)


main("../taiga")
