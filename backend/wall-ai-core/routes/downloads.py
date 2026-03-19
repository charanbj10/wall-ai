from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from services import download_service, image_service
from core.security import get_current_user

from kafka_client import producer

router = APIRouter(prefix="/downloads", tags=["Downloads"])


@router.post("/")
def create_download(
    imageid: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    download =  download_service.create_download(db, user.uid, imageid)

    image = image_service.get_image(db, imageid)

    try:
        producer.send_download_event(
            user_id  = str(user.uid),
            image_id = str(imageid),
            topic    = image.topic,
            hashtags = image.hashtags or [],
            name = image.name
        )
    except Exception as e:
        print(f"[Kafka] Failed to send event: {e}")

    return download


@router.get("/me")
def get_my_downloads(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return download_service.get_my_downloads(db, user.uid)