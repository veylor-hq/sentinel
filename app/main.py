from datetime import time
import os
from asyncio import run
from beanie import init_beanie
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import db
from app.core.config import config
from api.router import router as api_router
from app.core.email import send_email
from app.core.jwt import FastJWT
from models.models import StepTemplate, User, Mission, Step, Location, Note, MissionTemplate

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
            StepTemplate,
        ],
    )

    yield


def get_application():
    _app = FastAPI(title=config.PROJECT_NAME, lifespan=lifespan)

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return _app


app = get_application()


# health check
@app.get("/health")
async def health():   
    return {"status": "ok"}
    


@app.get("/verify")
async def verify_email_event(email: str, token: str):
    decoded_token = await FastJWT().decode(token)
    if decoded_token.email != email:
        raise HTTPException(400, "Invalid token")
    
    user = await User.find_one(User.email == email)
    if not user:
        raise HTTPException(400, "User not found")
    
    if user.email_verified:
        return {"message": "Email already verified"}
    
    user.email_verified = True
    await user.save()
    
    return {"message": "Email verified successfully"}

app.include_router(api_router)