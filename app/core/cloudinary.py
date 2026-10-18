"""Cloudinary image hosting.

Credentials come from settings and are applied once at import time, so any
module that imports this is ready to upload.
"""

import asyncio
import cloudinary
import cloudinary.uploader
from ..config import settings

# secure=True forces HTTPS delivery URLs.
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

async def upload_image_to_cloudinary(file_obj, folder: str = "spaces") -> str:
    """Uploads a file object to Cloudinary and returns its secure URL.

    The uploader is synchronous, so the call is pushed onto a worker thread to
    keep the event loop free while the request is in flight.
    """
    result = await asyncio.to_thread(
        cloudinary.uploader.upload,
        file_obj,
        folder=folder,
    )
    return result.get("secure_url")