from fastapi import APIRouter
from app.api.endpoints import chat, process_files

api_router = APIRouter()

print("Registering routes...")


api_router.include_router(
    chat.router,
    prefix="",
    tags=["chat"]
)

api_router.include_router(
    process_files.router,
    prefix="",
    tags=["process_files"]
)

