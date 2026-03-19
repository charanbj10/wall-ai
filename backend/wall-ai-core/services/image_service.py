from sqlalchemy.orm import Session
from db import models
import uuid
from schemas.schema import ImageCreate
from milvus.indexer import index_single_image


def create_image(db: Session, data: ImageCreate, uid: str):
    print(data)
    image = models.Image(
        name     = data.name,
        topic    = data.topic,
        hashtags = data.hashtags,
        postedBy = uid,
        s3url    = data.s3url,
    )

    print(image)

    db.add(image)
    db.commit()
    db.refresh(image)

    index_single_image(image.id, image.name, image.topic, image.hashtags)

    return image


def get_image(db: Session, image_id: int):
    return db.query(models.Image).filter(models.Image.id == image_id).first()


def get_images(db: Session, topic=None, hashtag=None, search=None, skip=0, limit=10):
    query = db.query(models.Image)

    if topic:
        query = query.filter(models.Image.topic == topic)

    if hashtag:
        query = query.filter(models.Image.hashtags.any(hashtag))

    if search:
        query = query.filter(models.Image.topic.ilike(f"%{search}%"))

    return query.offset(skip).limit(limit).all()