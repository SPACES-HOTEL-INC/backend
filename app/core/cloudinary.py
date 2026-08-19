import asyncio
import cloudinary
import cloudinary.uploader
from ..config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

async def upload_image_to_cloudinary(file_obj, folder: str = "spaces") -> str:
    """Uploads a file object to Cloudinary and returns its secure URL."""
    result = await asyncio.to_thread(
        cloudinary.uploader.upload,
        file_obj,
        folder=folder,
    )
    return result.get("secure_url")