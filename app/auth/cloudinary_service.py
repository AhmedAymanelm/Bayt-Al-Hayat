import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os

load_dotenv(override=True)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


async def upload_profile_picture(file_bytes: bytes, user_id: str) -> str:
    """Upload profile picture to Cloudinary and return the URL"""
    result = cloudinary.uploader.upload(
        file_bytes,
        folder="abrag/profile_pictures",
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
    public_id = f"abrag/profile_pictures/{user_id}"
    cloudinary.uploader.destroy(public_id, resource_type="image")
