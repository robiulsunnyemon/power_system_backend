import cloudinary
import cloudinary.uploader
import cloudinary.api
from fastapi import UploadFile
import os
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

async def upload_image(file: UploadFile, folder: str = "jorden/profiles"):
    """
    Uploads an image to Cloudinary and returns the result.
    """
    try:
        # Read file content
        file_content = await file.read()
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file_content,
            folder=folder,
            resource_type="image"
        )
        return result
    except Exception as e:
        print(f"Cloudinary Upload Error: {e}")
        return None
    finally:
        await file.seek(0) # Reset file pointer for future use if needed

def delete_image(public_id: str):
    """
    Deletes an image from Cloudinary using its public_id.
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result
    except Exception as e:
        print(f"Cloudinary Delete Error: {e}")
        return None

def get_public_id_from_url(url: str):
    """
    Extracts the public_id from a Cloudinary URL.
    Example URL: https://res.cloudinary.com/cloud_name/image/upload/v123456789/folder/image_name.jpg
    Public ID: folder/image_name
    """
    try:
        # Split by '/upload/'
        parts = url.split('/upload/')
        if len(parts) < 2:
            return None
        
        # After /upload/ there might be a version string like 'v123456789/'
        after_upload = parts[1]
        sub_parts = after_upload.split('/')
        
        # If the first part starts with 'v' and is numeric, it's the version
        start_index = 1 if sub_parts[0].startswith('v') and sub_parts[0][1:].isdigit() else 0
        
        # Join the remaining parts and remove the file extension
        public_id_with_ext = "/".join(sub_parts[start_index:])
        public_id = public_id_with_ext.rsplit('.', 1)[0]
        return public_id
    except Exception:
        return None
