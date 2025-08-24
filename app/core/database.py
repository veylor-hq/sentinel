import motor.motor_asyncio
from app.core.config import config

client = motor.motor_asyncio.AsyncIOMotorClient(
    config.DATABASE_URL, uuidRepresentation="standard"
)
db = client[config.DATABASE_NAME]