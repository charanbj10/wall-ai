from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import engine, Base
from routes import users, images, downloads, auth, recommend
from contextlib import asynccontextmanager
from kafka_client.consumer import start_consumer, stop_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_consumer()   # starts on FastAPI boot
    yield
    stop_consumer()    # stops on FastAPI shutdown

app = FastAPI(lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# Create tables
Base.metadata.create_all(bind=engine)

app.include_router(users.router)
app.include_router(images.router)
app.include_router(downloads.router)
app.include_router(auth.router)
app.include_router(recommend.router)