import boto3
import os
from dotenv import load_dotenv
import base64
from fastapi import HTTPException, status
from botocore.exceptions import ClientError
import uuid


load_dotenv()


AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION            = os.getenv("AWS_REGION")
S3_BUCKET             = os.getenv("AWS_S3_BUCKET")

def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )


def upload_base64_to_s3(base64_image: str, filename: str, postedBy: str) -> str:

    if "," in base64_image:
        header, base64_data = base64_image.split(",", 1)
        content_type = header.split(":")[1].split(";")[0]
    else:
        base64_data  = base64_image
        content_type = "image/jpeg"
 
    # Step 2 — decode
    try:
        image_bytes = base64.b64decode(base64_data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 image data"
        )
 
    # Step 3 — upload to S3
    s3_key = f"wallpapers/{postedBy}/{filename}"
    try:
        s3 = get_s3_client()
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=image_bytes,
            ContentType=content_type,
            ACL="public-read",
        )
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"S3 upload failed: {str(e)}"
        )
 
    s3_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
    return s3_url