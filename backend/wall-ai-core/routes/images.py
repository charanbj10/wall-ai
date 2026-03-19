from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.schema import ImageCreate, ImageUploadRequest
from services import image_service, s3
from core.security import get_current_user
import uuid
from kafka_client import producer


router = APIRouter(prefix="/images", tags=["Images"])


@router.post("/")
def create_image(
    data: ImageCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)   # ✅ from token
):
    return image_service.create_image(db, data, user.uid)


@router.get("/{image_id}")
def get_image(image_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    image =  image_service.get_image(db, image_id)

    try:

        producer.send_view_event(
            user_id  = str(user.uid),
            image_id = str(image.id),
            topic    = image.topic,
            hashtags = image.hashtags or [],
            name = image.name
        )
    except Exception as e:
        print(f"[Kafka] Failed to send event: {e}")

    return image


@router.post("/upload")
async def upload_image(
    payload: ImageUploadRequest,
    user: str = Depends(get_current_user),   # Bearer token required
    db: Session = Depends(get_db)
):
    if not payload.base64_image:
        raise HTTPException(status_code=400, detail="base64_image is required")
    if not payload.name:
        raise HTTPException(status_code=400, detail="name is required")
    if not payload.topic:
        raise HTTPException(status_code=400, detail="topic is required")
 
    # Generate a clean filename
    extension = "jpg"
    if "png" in payload.base64_image[:30]:
        extension = "png"
    elif "jpeg" in payload.base64_image[:30]:
        extension = "jpeg"
    elif "webp" in payload.base64_image[:30]:
        extension = "webp"
    filename = f"{payload.name.replace(' ', '_').lower()}_{uuid.uuid4().hex[:8]}.{extension}"
 
    # Upload to S3 — get back the public URL
    s3_url = s3.upload_base64_to_s3(payload.base64_image, filename, user.uid)
 
    return image_service.create_image(db, ImageCreate(topic= payload.topic, hashtags= payload.hashtags, name= payload.name, s3url= s3_url), user.uid)


@router.get("/")
def get_images(
    topic: str = Query(None),
    hashtag: str = Query(None),
    search: str = Query(None),
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    return image_service.get_images(db, topic, hashtag, search, skip, limit)