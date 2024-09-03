from PIL import Image


def resize_and_crop(image: Image, size: tuple) -> Image:
    """Resize and crop the image to the target size while maintaining the aspect ratio."""
    target_width, target_height = size
    img_width, img_height = image.size

    # Calculate aspect ratios
    aspect_ratio = img_width / img_height
    target_aspect_ratio = target_width / target_height

    if aspect_ratio > target_aspect_ratio:
        # Image is wider than target
        new_width = int(target_height * aspect_ratio)
        new_height = target_height
    else:
        # Image is taller than target
        new_width = target_width
        new_height = int(target_width / aspect_ratio)

    # Resize the image
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)

    # Crop the center
    left = (new_width - target_width) / 2
    top = (new_height - target_height) / 2
    right = (new_width + target_width) / 2
    bottom = (new_height + target_height) / 2

    return resized_image.crop((left, top, right, bottom))
