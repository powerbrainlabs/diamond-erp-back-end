"""
Utility for generating QR codes for certificates
"""
import io
from typing import Optional
import qrcode
from ..core.minio_client import minio_client


def generate_qr_code_image(data: str, size: int = 200) -> io.BytesIO:
    """
    Generate a QR code image from data string
    
    Args:
        data: The data to encode in the QR code
        size: The size of the QR code image in pixels
    
    Returns:
        BytesIO object containing the PNG image
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction for print
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize to desired size
    img = img.resize((size, size))
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes


def save_qr_code_to_minio(certificate_uuid: str, qr_url: str, size: int = 200) -> Optional[str]:
    """
    Generate QR code and save it to MinIO
    
    Args:
        certificate_uuid: UUID of the certificate
        qr_url: The URL to encode in the QR code
        size: Size of the QR code image
    
    Returns:
        Path to the QR code in MinIO (bucket/object_name) or None if failed
    """
    try:
        # Generate QR code image
        qr_image = generate_qr_code_image(qr_url, size)
        qr_image_bytes = qr_image.getvalue()
        qr_image_length = len(qr_image_bytes)
        
        # Create object name
        qr_filename = f"{certificate_uuid}_qr.png"
        bucket_name = "certificates"
        
        # Ensure bucket exists
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
        
        # Upload to MinIO
        qr_image.seek(0)  # Reset to beginning
        minio_client.put_object(
            bucket_name=bucket_name,
            object_name=qr_filename,
            data=qr_image,
            length=qr_image_length,
            content_type="image/png"
        )
        
        return f"{bucket_name}/{qr_filename}"
    except Exception as e:
        print(f"Failed to generate/save QR code: {e}")
        return None

