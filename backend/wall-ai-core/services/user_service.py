from sqlalchemy.orm import Session
from db import models


def get_user(db: Session, uid: str):
    return db.query(models.User).filter(models.User.uid == uid).first()


def get_users(db: Session, skip=0, limit=10):
    return db.query(models.User).offset(skip).limit(limit).all()