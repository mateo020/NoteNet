from fastapi import APIRouter
from app.api.endpoints import chat

api_router = APIRouter()

print("Registering routes...")


api_router.include_router(
    chat.router,
    prefix="",
    tags=["chat"]
)

