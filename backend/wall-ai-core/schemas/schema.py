from pydantic import BaseModel
from typing import List, Optional


class UserCreate(BaseModel):
    uid: str
    email: str
    name: str


class ImageCreate(BaseModel):
    s3url: str
    name: str
    topic: str
    hashtags: List[str]


class DownloadCreate(BaseModel):
    imageid: int
    uid: str


class SignUpRequest(BaseModel):
    email: str
    name: str
    password: str


class SignInRequest(BaseModel):
    email: str
    password: str

class ImageUploadRequest(BaseModel):

    base64_image: str
    name: str
    topic: str
    hashtags: Optional[list[str]] = []
 
 
class ImageUploadResponse(BaseModel):
    id: int
    topic: str
    postedBy: str
    hashtags: list[str]
    s3url: str
    name: str
    timestamp: str