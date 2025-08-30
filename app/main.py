import os
from asyncio import run
from beanie import init_beanie
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import db
from app.core.config import config
from api.router import router as api_router
from models.models import User, Mission, Step, Location, Note, MissionTemplate

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_beanie(
        database=db,
        document_models=[
            User,
            Mission,
            Step,
            Note,
            Location,
            MissionTemplate,
        ],
    )

    yield


def get_application():
    _app = FastAPI(title=config.PROJECT_NAME, lifespan=lifespan)

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in config.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return _app


app = get_application()


# health check
@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(api_router)