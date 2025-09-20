from time import time
from app.core.config import config
from app.core.email import send_email
from app.core.jwt import DecodedToken, FastJWT
from models.models import Mission, Step, User
from app.core.password_utils import get_password_hash, verify_password
from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field


profile_router = APIRouter(prefix="/profile")


@profile_router.get("/")
async def profile_event(request: Request):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
    }
    

@profile_router.post("/set_email")
async def set_email_event(request: Request, email: str, background_tasks: BackgroundTasks):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    
    if await User.find_one(User.email == email):
        raise HTTPException(400, "Email already in use")
    
    if user.email:
        raise HTTPException(400, "Email already set, use change_email endpoint")

    user.email = email
    await user.save()

    token = await FastJWT().encode({
        "id": str(user.id),
        "username": user.username,
        "email": email,
    }, 24*3600)

    verification_link = f"{config.API_BASE_URL}/verify?email={email}&token={token}"

    background_tasks.add_task(send_email,
        to=email,
        subject="Verify your email address for Sentinel",       
        body="Please click the link below to verify your email address:\n\n{verification_link} \n\nIf you did not request this email, please ignore it.".format(verification_link=verification_link),
    )
     
    return {"message": "Verification email sent"}


@profile_router.post("/resend_verification")
async def resend_verification_event(request: Request, background_tasks: BackgroundTasks): 
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    
    if not user.email:
        raise HTTPException(400, "Email not set")
    
    if user.email_verified:
        return {"message": "Email already verified"}
    
    token = await FastJWT().encode({
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
    }, 24*3600)

    verification_link = f"{config.API_BASE_URL}/verify?email={user.email}&token={token}"

    background_tasks.add_task(send_email,
        to=user.email,
        subject="Verify your email address for Sentinel",       
        body="Please click the link below to verify your email address:\n\n{verification_link} \n\nIf you did not request this email, please ignore it.".format(verification_link=verification_link),
    )
     
    return {"message": "Verification email sent"}


# change password:
class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)

@profile_router.post("/change_password")
async def change_password_event(request: Request, body: ChangePasswordRequest, background_tasks: BackgroundTasks):
    token: DecodedToken = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    
    if body.current_password == body.new_password:
        raise HTTPException(400, "New password must be different from current password")

    if not verify_password(body.current_password, user.password):
        raise HTTPException(400, "Current password is incorrect")
    
    user.password = get_password_hash(body.new_password)
    await user.save()

    background_tasks.add_task(send_email,
        to=user.email,
        subject="Password changed for Sentinel",
        body="Your password has been changed successfully. If you did not perform this action, please contact support immediately.",
    )

    return {"message": "Password changed successfully"}