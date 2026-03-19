from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{uid}")
def get_user(uid: str, db: Session = Depends(get_db)):
    return user_service.get_user(db, uid)


@router.get("/")
def get_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return user_service.get_users(db, skip, limit)