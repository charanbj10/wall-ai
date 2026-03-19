from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY
from db.database import Base


class User(Base):
    __tablename__ = "users"

    uid = Column(String, primary_key=True)
    email = Column(String, unique=True)
    name = Column(String)


class Credential(Base):
    __tablename__ = "credentials"

    uid = Column(String, ForeignKey("users.uid"), primary_key=True)
    password_hash = Column(String)


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    s3url = Column(String)
    name = Column(String)
    topic = Column(String)
    hashtags = Column(ARRAY(String))
    postedBy = Column(String, ForeignKey("users.uid"))
    timestamp = Column(TIMESTAMP, server_default=func.now())


class Download(Base):
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True)
    imageid = Column(Integer, ForeignKey("images.id"))
    uid = Column(String, ForeignKey("users.uid"))
    timestamp = Column(TIMESTAMP, server_default=func.now())