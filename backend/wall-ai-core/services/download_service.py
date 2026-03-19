from sqlalchemy.orm import Session
from db import models


def create_download(db: Session, uid: str, imageid: int):
    download = models.Download(uid=uid, imageid=imageid)
    db.add(download)
    db.commit()
    db.refresh(download)
    return download


def get_my_downloads(db: Session, uid: str):
    return db.query(models.Download).filter(models.Download.uid == uid).all()