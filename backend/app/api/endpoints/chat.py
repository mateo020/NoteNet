from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import os
from pathlib import Path
from .process_files import process_and_combine_files

router = APIRouter()

# @router.post("/")
# def read_root():
#     return {"message": "FastAPI is working with CORS!"}


# # New GET route
# @router.get("/")
# def get_api_root():
#     return {"message": "GET /api is alive!"}

@router.post("/upload_file")
async def upload_file(file: UploadFile = File(...)):
    # Define allowed file types
    allowed_audio_types = ["audio/mpeg", "audio/wav", "audio/ogg", "audio/mp3"]
    allowed_pdf_types = ["application/pdf"]
    allowed_image_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    
    # Check file type
    content_type = file.content_type
    
    if content_type not in allowed_audio_types + allowed_pdf_types + allowed_image_types:
        raise HTTPException(
            status_code=400,
            detail="File type not allowed. Please upload an audio file, PDF, or image."
        )
    
    # Create uploads directory if it doesn't exist
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    # Generate a unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{file.filename}"
    
    # Save the file
    file_path = upload_dir / unique_filename
    try:
        contents = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Process the file based on its type
        try:
            if content_type in allowed_audio_types:
                combined_file = process_and_combine_files(audio_path=str(file_path))
                file_type = "audio"
                print(combined_file)
            else:
                combined_file = process_and_combine_files(document_path=str(file_path))
                file_type = "document"
                print(combined_file)
            return {
                "message": f"{file_type.capitalize()} file processed successfully",
                "filename": unique_filename,
                "content_type": content_type,
                "file_path": str(file_path),
                "output_file": combined_file
            }
        except ValueError as ve:
            raise HTTPException(
                status_code=400,
                detail=str(ve)
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing file: {str(e)}"
            )
    except Exception as e:
        # Clean up the uploaded file if processing failed
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while handling the file: {str(e)}"
        )