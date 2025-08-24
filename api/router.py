from fastapi import APIRouter


router = APIRouter(prefix="/api")


@router.get("/")
def api_router():
    return {
        "status": "healthy",
        "message": "Refer to documentation for usage help."
    }