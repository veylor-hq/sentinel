from typing import List, Optional, Union

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    PROJECT_NAME: str
    BACKEND_CORS_ORIGINS: Optional[List[str]] = ["*"]

    DATABASE_NAME: str
    DATABASE_URL: str

    API_BASE_URL: str

    JWT_SECRET_KEY: str
    PASSWORDS_SALT_SECRET_KEY: str


    @field_validator("BACKEND_CORS_ORIGINS")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v

    class Config:
        case_sensitive = True
        env_file = ".env"


config = Config()