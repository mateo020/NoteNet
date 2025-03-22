from openai import OpenAI
import pytesseract
from PIL import Image
import PyPDF2
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def transcribe_audio(file_path):
    """
    Transcribe audio file using OpenAI's Whisper API
    """
    try:
        # Open the audio file in binary mode
        with open(file_path, "rb") as audio_file:
            # Transcribe the audio using the latest OpenAI API syntax
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
            return transcript.text
    except Exception as e:
        if "insufficient_quota" in str(e):
            print("Error: You have exceeded your API quota. Please check your billing and plan details.")
        else:
            print(f"Error transcribing audio: {e}")
        return ""

def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from image using pytesseract
    """
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error extracting text from image: {str(e)}")
        return ""

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF file
    """
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return ""

def process_and_combine_files(audio_path: str = None, document_path: str = None) -> str:
    """
    Process audio and document files, then combine their text.
    Can handle either single file uploads or both files.
    
    Args:
        audio_path (str, optional): Path to the audio file
        document_path (str, optional): Path to the document file (PDF or image)
    
    Returns:
        str: Path to the combined text file
    
    Raises:
        ValueError: If neither file path is provided
    """
    if not audio_path and not document_path:
        raise ValueError("At least one file path must be provided")
    
    combined_text = []
    
    # Process audio file if provided
    if audio_path and os.path.exists(audio_path):
        try:
            audio_text = transcribe_audio(audio_path)
            if audio_text:
                combined_text.append("=== Audio Transcription ===\n")
                combined_text.append(audio_text)
                combined_text.append("\n")
            else:
                print(f"Warning: No text was extracted from audio file: {audio_path}")
        except Exception as e:
            print(f"Error processing audio file {audio_path}: {str(e)}")
    
    # Process document file if provided
    if document_path and os.path.exists(document_path):
        try:
            file_extension = os.path.splitext(document_path)[1].lower()
            if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                doc_text = extract_text_from_image(document_path)
            elif file_extension == '.pdf':
                doc_text = extract_text_from_pdf(document_path)
            else:
                print(f"Warning: Unsupported document type: {file_extension}")
                doc_text = ""
                
            if doc_text:
                combined_text.append("=== Document Text ===\n")
                combined_text.append(doc_text)
            else:
                print(f"Warning: No text was extracted from document: {document_path}")
        except Exception as e:
            print(f"Error processing document file {document_path}: {str(e)}")
    
    if not combined_text:
        raise ValueError("No text was extracted from any of the provided files")
    
    # Combine all text
    final_text = "\n".join(combined_text)
    
    # Create files directory if it doesn't exist
    files_dir = Path("backend/app/files")
    files_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename based on input files
    if audio_path and document_path:
        filename = "combined_audio_and_document.txt"
    elif audio_path:
        filename = "audio_transcription.txt"
    else:
        filename = "document_text.txt"
    
    # Save combined text to file
    output_file = files_dir / filename
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_text)
    
    return str(output_file) 