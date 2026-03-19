from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Image
from ml.recommend import recommend

router = APIRouter(prefix="/recommend", tags=["recommend"])

@router.get("/{user_id}")
def get_recommendations(
    user_id: str,
    limit:   int = Query(default=20, ge=1, le=100),
    topic:   str = Query(default=None),
    db:      Session = Depends(get_db),
):
    result    = recommend(user_id=user_id, limit=limit, topic=topic)
    image_ids = [img["image_id"] for img in result["images"]]

    # ONE batch query — get s3url for all images
    db_images = db.query(Image).filter(Image.id.in_(image_ids)).all()
    db_map    = {str(img.id): img for img in db_images}

    # Merge — attach s3url to each recommended image
    result["images"] = [
        {
            "id":        img["image_id"],
            "name":      img["name"],
            "topic":     img["topic"],
            "hashtags":  db_map.get(str(img["image_id"])).hashtags if db_map.get(str(img["image_id"])) else None,
            "score":     img.get("score", 0),
            "s3url":     db_map.get(str(img["image_id"])).s3url if db_map.get(str(img["image_id"])) else None,
            "timestamp": str(db_map.get(str(img["image_id"])).timestamp) if db_map.get(str(img["image_id"])) else None,
        }
        for img in result["images"]
    ]
    return result