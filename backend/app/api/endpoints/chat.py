from fastapi import APIRouter, HTTPException, UploadFile, File, Form
router = APIRouter()

@router.post("/")
def read_root():
    return {"message": "FastAPI is working with CORS!"}


# New GET route
@router.get("/")
def get_api_root():
    return {"message": "GET /api is alive!"}