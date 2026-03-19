from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from schemas.schema import SignUpRequest, SignInRequest
from services import auth

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup")
def signup(data: SignUpRequest, db: Session = Depends(get_db)):
    return auth.signup(
        db,
        email=data.email,
        name=data.name,
        password=data.password
    )


@router.post("/signin")
def signin(data: SignInRequest, db: Session = Depends(get_db)):
    return auth.signin(
        db,
        email=data.email,
        password=data.password
    )