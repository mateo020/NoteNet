from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional, Dict, List
import os
from pathlib import Path
from .process_files import process_and_combine_files
import json

router = APIRouter()

# @router.post("/")
# def read_root():
#     return {"message": "FastAPI is working with CORS!"}


# # New GET route
# @router.get("/")
# def get_api_root():
#     return {"message": "GET /api is alive!"}

@router.post("/upload_file")
async def upload_file(files: List[UploadFile] = File(...)):
    # Define allowed file types
    allowed_audio_types = ["audio/mpeg", "audio/wav", "audio/ogg", "audio/mp3", "audio/x-m4a", "audio/m4a"]
    allowed_pdf_types = ["application/pdf"]
    allowed_image_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    
    # Create uploads directory if it doesn't exist
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    audio_path = None
    document_path = None
    
    try:
        print("\n=== File Upload Debug ===")
        print(f"Processing {len(files)} files")
        
        for file in files:
            content_type = file.content_type
            print(f"\nProcessing file: {file.filename}")
            print(f"Content type: {content_type}")
            
            if content_type not in allowed_audio_types + allowed_pdf_types + allowed_image_types:
                print(f"❌ Unsupported file type: {content_type}")
                raise HTTPException(
                    status_code=400,
                    detail=f"File type not allowed. Please upload an audio file (MP3, WAV, OGG, M4A), PDF, or image."
                )
            
            # Save the file
            file_path = upload_dir / file.filename
            contents = await file.read()
            
            with open(file_path, "wb") as f:
                f.write(contents)
            
            # Determine file type and store path
            if content_type in allowed_audio_types:
                if audio_path:
                    raise HTTPException(
                        status_code=400,
                        detail="Only one audio file can be uploaded at a time"
                    )
                audio_path = str(file_path)
                print("✅ Audio file saved")
            else:
                if document_path:
                    raise HTTPException(
                        status_code=400,
                        detail="Only one document file can be uploaded at a time"
                    )
                document_path = str(file_path)
                print("✅ Document file saved")
        
        # Process the files
        try:
            print("\nProcessing files...")
            combined_file = await process_and_combine_files(
                audio_path=audio_path,
                document_path=document_path
            )
            
            print(f"✅ Files processed successfully")
            print(f"Combined file path: {combined_file}")
            print("=== End File Upload Debug ===\n")
            
            return {
                "message": "Files processed successfully",
                "files": [
                    {"filename": os.path.basename(path), "type": "audio" if path == audio_path else "document"}
                    for path in [audio_path, document_path] if path
                ],
                "output_file": combined_file
            }
            
        except ValueError as ve:
            print(f"❌ ValueError during file processing: {str(ve)}")
            raise HTTPException(
                status_code=400,
                detail=str(ve)
            )
        except Exception as e:
            print(f"❌ Error processing files: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing files: {str(e)}"
            )
            
    except Exception as e:
        # Clean up any uploaded files if processing failed
        for path in [audio_path, document_path]:
            if path and os.path.exists(path):
                os.remove(path)
        print(f"❌ Error handling files: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while handling the files: {str(e)}"
        )

@router.get("/latest_entities")
async def get_latest_entities():
    """
    Get the most recently created entities and relationships files.
    """
    entities_dir = Path("backend/app/entities")
    if not entities_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="No entities found"
        )
    
    # Get all JSON files in the entities directory
    entity_files = list(entities_dir.glob("entities_*.json"))
    if not entity_files:
        raise HTTPException(
            status_code=404,
            detail="No entity files found"
        )
    
    # Get the most recent file
    latest_file = max(entity_files, key=lambda x: x.stat().st_mtime)
    unique_id = latest_file.stem.split('_')[1]  # Extract the unique ID from the filename
    
    try:
        # Read entities file
        with open(latest_file, 'r', encoding='utf-8') as f:
            entities = json.load(f)
        
        # Read corresponding relationships file
        relationships_file = entities_dir / f"relationships_{unique_id}.json"
        if relationships_file.exists():
            with open(relationships_file, 'r', encoding='utf-8') as f:
                relationships = json.load(f)
        else:
            relationships = []
        
        return {
            "entities": entities,
            "relationships": relationships
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading files: {str(e)}"
        )

@router.get("/latest_entities/nodes")
async def get_latest_nodes():
    """Get the latest nodes file."""
    entities_dir = Path("backend/app/entities")
    if not entities_dir.exists():
        raise HTTPException(status_code=404, detail="Entities directory not found")
    
    nodes_file = entities_dir / "nodes.json"
    if not nodes_file.exists():
        raise HTTPException(status_code=404, detail="No nodes file found")
    
    try:
        with open(nodes_file, 'r', encoding='utf-8') as f:
            nodes = json.load(f)
        return nodes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading nodes file: {str(e)}")

@router.get("/latest_entities/relationships")
async def get_latest_relationships():
    """Get the latest relationships file."""
    entities_dir = Path("backend/app/entities")
    if not entities_dir.exists():
        raise HTTPException(status_code=404, detail="Entities directory not found")
    
    relationships_file = entities_dir / "relationships.json"
    if not relationships_file.exists():
        raise HTTPException(status_code=404, detail="No relationships file found")
    
    try:
        with open(relationships_file, 'r', encoding='utf-8') as f:
            relationships = json.load(f)
        return relationships
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading relationships file: {str(e)}")