import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()
cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
  api_key = os.getenv('CLOUDINARY_API_KEY'),
  api_secret = os.getenv('CLOUDINARY_API_SECRET')
)

try:
    response = cloudinary.uploader.upload(
        '/Users/ahmed/abrag/imge/Glowing bull amidst cosmic clouds.png',
        folder='zodiac_signs'
    )
    print('SUCCESS_URL:' + response['secure_url'])
except Exception as e:
    print('Error:', e)
