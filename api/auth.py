from app.core.jwt import FastJWT
from models.models import User
from app.core.password_utils import get_password_hash, verify_password
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field


class AuthSchema(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: PydanticObjectId = Field(..., alias='id')
    username: str

    class Config:
        json_encoders = {PydanticObjectId: str}

auth_router = APIRouter(prefix="/auth")

@auth_router.post("/signup", response_model=UserOut)
async def signup_event(payload: AuthSchema) -> UserOut:
    if await User.find_one({"username": payload.username}):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    user: User = User(
        username=payload.username,
        password=get_password_hash(payload.password),
    )
    user: User = await user.insert()
    return UserOut(id=user.id, username=user.username)


@auth_router.post("/signin")
async def signin_event(payload: AuthSchema):
    user = await User.find_one({"username": payload.username})
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Bad username or password")

    jwt_token = await FastJWT().encode(optional_data={
        "id": str(user.id),
        "username": payload.username,
    })

    return {"token": jwt_token}


# TODO: hould this be a private router instead?
@auth_router.get("/me", response_model=UserOut)
async def me_event(request: Request) -> UserOut:
    token: dict = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    return UserOut(id=user.id, username=user.username)


@auth_router.get("/verify")
async def verify_event(request: Request):
    token: dict = await FastJWT().decode(request.headers["Authorization"])
    user = await User.get(token.id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    return {"status": "valid"}