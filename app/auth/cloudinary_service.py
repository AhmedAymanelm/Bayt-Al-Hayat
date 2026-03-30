import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os
from dotenv import load_dotenv
from app.utils.settings_helper import get_env_or_db

load_dotenv(override=True)

async def _init_cloudinary():
    cloudinary.config(
        cloud_name=await get_env_or_db("cloudinary_cloud_name"),
        api_key=await get_env_or_db("cloudinary_api_key"),
        api_secret=await get_env_or_db("cloudinary_api_secret"),
        secure=True
    )

async def upload_profile_picture(file_bytes: bytes, user_id: str) -> str:
    """Upload profile picture to Cloudinary and return the URL"""
    await _init_cloudinary()
    result = cloudinary.uploader.upload(
        file_bytes,
        folder="bayt_al_hayat/profile_pictures",
        public_id=str(user_id),
        overwrite=True,
        resource_type="image",
        transformation=[
            {"width": 400, "height": 400, "crop": "fill", "gravity": "face"},
            {"quality": "auto", "fetch_format": "auto"}
        ]
    )
    return result["secure_url"]


async def delete_profile_picture(user_id: str):
    """Delete profile picture from Cloudinary"""
    await _init_cloudinary()
    public_id = f"bayt_al_hayat/profile_pictures/{user_id}"
    cloudinary.uploader.destroy(public_id, resource_type="image")
