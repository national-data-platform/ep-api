# api/routes/default_routes/get.py

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def index(request: Request):
    return "API is running successfully."
