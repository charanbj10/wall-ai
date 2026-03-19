import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy.orm import Session
from db.database import get_db
from db import models
from milvus.client import get_images_collection
from milvus.embeddings import embed_image
from fastapi import Depends

def format_hashtags(tags):
    if not tags:
        return ""

    return ",".join([
        str(tag).strip()
        for tag in tags
        if tag is not None and str(tag).strip() != ""
    ])

def index_all_images(db: Session):
    """
    Step 1 — Run once to populate Milvus with all existing PostgreSQL images.
    python milvus/indexer.py
    """

    db = next(get_db())
    print ("DB activated")

    col = get_images_collection()

    print("hello")

    try:
        images = db.query(models.Image).all()
        print(f"[Indexer] Found {len(images)} images in PostgreSQL")

        if not images:
            print("[Indexer] No images found")
            return

        image_id   = []
        embedding = []
        topic      = []
        name       = []
        hashtags   = []

        for img in images:
            print(f"  Embedding [{img.id}] {img.name} — {img.topic}")
            emb = embed_image(
                name=img.name or "",
                topic=img.topic or "",
                hashtags=img.hashtags or [],
            )
            image_id.append(str(img.id))
            embedding.append(emb)
            topic.append(img.topic or "")
            name.append(img.name or "")
            
            hashtag_str = format_hashtags(img.hashtags)
            hashtags.append(hashtag_str)

        print(image_id, topic, name,hashtags)
        print(len(image_id), len(embedding), len(topic), len(name), len(hashtags))
        col.insert([image_id, embedding, topic, name, hashtags])
        col.flush()
        print(f"[Indexer] Indexed {len(images)} images into Milvus!")

    except Exception as e:
        print(f"[Indexer] Error: {e}")
        raise
    # finally:
    #     db.close()


def index_single_image(image_id: int, name: str, topic: str, hashtag: list):
    """
    Call this from POST /images/ to keep Milvus in sync.

    from milvus.indexer import index_single_image
    index_single_image(img.id, img.name, img.topic, img.hashtag)
    """
    hashtags = format_hashtags(hashtag)

    col = get_images_collection()
    emb = embed_image(name, topic, hashtag)
    col.insert([[str(image_id)], [emb], [topic], [name], [hashtags]])
    col.flush()
    print(f"[Indexer] Indexed new image [{image_id}] {name}")


if __name__ == "__main__":
    index_all_images(db=Session)