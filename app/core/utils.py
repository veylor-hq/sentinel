from fastapi import APIRouter


def include_routers(app: APIRouter, *routers: APIRouter):
    """
    Include multiple APIRouter instances into the FastAPI app at once.

    Args:
        app (FastAPI): FastAPI app instance.
        *routers (APIRouter): Routers to include.
    """
    for router in routers:
        app.include_router(router)
