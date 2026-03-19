from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import uuid

from db import models
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 🔑 Hash password
def hash_password(password: str):
    return pwd_context.hash(password)


# 🔑 Verify password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# 🔐 Create JWT token
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# 🟢 SIGN UP (UID generated here)
def signup(db: Session, email: str, name: str, password: str):
    # check existing
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        return {"error": "User already exists"}

    uid = str(uuid.uuid4())  # ✅ backend UID

    user = models.User(uid=uid, email=email, name=name)
    db.add(user)
    db.commit() 

    hashed = hash_password(password)
    cred = models.Credential(uid=uid, password_hash=hashed)
    db.add(cred)

    db.commit()

    return {"message": "User created", "uid": uid}


# 🔵 SIGN IN (returns token)
def signin(db: Session, email: str, password: str):
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        return {"error": "User not found"}

    cred = db.query(models.Credential).filter(models.Credential.uid == user.uid).first()

    if not cred or not verify_password(password, cred.password_hash):
        return {"error": "Invalid credentials"}

    # 🔐 create token
    token = create_access_token({
        "sub": user.uid,
        "email": user.email
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "uid": user.uid,
        "email": user.email,
        "name": user.name
    }