from typing import List

import cloudinary
from cloudinary.uploader import upload
from config.config_manager import (
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
)


cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
)


async def upload_image(image: str):
    try:
        upload_result = upload(image)
        file_url = upload_result["secure_url"]
        print(f"Uploaded Image URL: {file_url}")
        return file_url
    except Exception as e:
        print(f"Error uploading image: {e}")
        return None
