from beanie import PydanticObjectId
import jwt
import datetime

from fastapi import HTTPException, Header
from pydantic import BaseModel

class DecodedToken(BaseModel):
    expire: float
    id: PydanticObjectId
    username: str
    email: str | None = None

class FastJWT:
    def __init__(self):
        self.secret_key = "secret key"


    async def encode(self, optional_data=None, expire=None):
        if not expire:
            expire = (datetime.datetime.now() + datetime.timedelta(days=30)).timestamp()

        token_json = {
            "expire": expire
        }

        if optional_data:
            token_json.update(optional_data)
        jwt_token = jwt.encode(token_json, self.secret_key, algorithm="HS256")

        return jwt_token
    

    async def decode(self, payload) -> DecodedToken:
        decoded_token = jwt.decode(payload, self.secret_key, algorithms=["HS256"])

        return DecodedToken(
            **decoded_token
        )


    async def login_required(self, Authorization=Header("Authorization")):
        try:
            if Authorization == "Authorization":
                raise
            
            jwt_token = await self.decode(Authorization)

            if jwt_token.expire < int(datetime.datetime.now().timestamp()):
                raise

        except Exception as e:
            print(e)
            raise HTTPException(status_code=401, detail="Unauthorized")