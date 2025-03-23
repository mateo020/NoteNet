from openai import OpenAI, AsyncOpenAI
import pytesseract
from PIL import Image
import PyPDF2
import os
from pathlib import Path
from dotenv import load_dotenv
import uuid
import json
from typing import Dict, List
# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def chunk_text(text: str, max_chunk_size: int = 4000) -> List[str]:
    """
    Split text into chunks that are suitable for API processing.
    Tries to split at sentence boundaries when possible.
    """
    sentences = text.split('.')
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence = sentence.strip() + '.'
        sentence_size = len(sentence)
        
        if current_size + sentence_size > max_chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_size = sentence_size
        else:
            current_chunk.append(sentence)
            current_size += sentence_size
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

async def extract_entities_and_concepts(text: str) -> Dict:
    """
    Extract key concepts and named entities from text using OpenAI API.
    Handles large texts by chunking them appropriately.
    """
    chunks = chunk_text(text)
    all_entities = {}
    
    for chunk in chunks:
        try:
            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts key concepts and named entities from text. Provide concise, relevant definitions in the context of the text."
                    },
                    {
                        "role": "user",
                        "content": f"""Given this text, please extract a list of concepts and named entities that are key to the text, as well as a brief dictionary-like entry defining the entity in the context of the text.
                        This should be presented in the form of a JSON object where each key is an entity name and the value is its description.
                        Only include entities that are explicitly mentioned or strongly implied in the text.
                        Be concise but informative in the descriptions.
                        
                        Text to analyze:
                        {chunk}"""
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Extract the JSON from the response
            response_text = response.choices[0].message.content
            try:
                # Try to find JSON in the response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    chunk_entities = json.loads(response_text[json_start:json_end])
                    all_entities.update(chunk_entities)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON from chunk: {e}")
                continue
                
        except Exception as e:
            print(f"Error processing chunk with OpenAI API: {e}")
            continue
    
    return all_entities

async def transcribe_audio(file_path):
    """
    Transcribe audio file using OpenAI's Whisper API
    """
    try:
        # Open the audio file in binary mode
        with open(file_path, "rb") as audio_file:
            # Transcribe the audio using the latest OpenAI API syntax
            transcript = await client.audio.transcriptions.create(
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

async def extract_relationships(entities: Dict) -> List[Dict]:
    """
    Extract relationships between entities using OpenAI API.
    Returns a list of edges suitable for a knowledge graph.
    """
    # Convert entities to a format suitable for the API
    entities_text = "\n".join([
        f"{entity}: {desc['description'] if isinstance(desc, dict) else desc}"
        for entity, desc in entities.items()
    ])
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a knowledge graph expert. Analyze the given entities and their descriptions to identify meaningful relationships between them.
                    Create relationships that capture how these entities are connected in the context of the text.
                    Return the relationships in a specific JSON format."""
                },
                {
                    "role": "user",
                    "content": f"""Given these entities and their descriptions, identify meaningful relationships between them.
                    Return a JSON array of relationships, where each relationship has:
                    - source: the name of the source entity
                    - target: the name of the target entity
                    - relation: a verb or preposition describing the relationship
                    - description: a brief explanation of the relationship
                    
                    Entities:
                    {entities_text}
                    
                    Return only the JSON array, no additional text."""
                }
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        # Extract the JSON from the response
        response_text = response.choices[0].message.content
        try:
            # Try to find JSON in the response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                relationships = json.loads(response_text[json_start:json_end])
                print(f"Found {len(relationships)} relationships")
                return relationships
        except json.JSONDecodeError as e:
            print(f"Error parsing relationships JSON: {e}")
            return []
            
    except Exception as e:
        print(f"Error extracting relationships with OpenAI API: {e}")
        return []

async def process_and_combine_files(audio_path: str = None, document_path: str = None) -> str:
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
            audio_text = await transcribe_audio(audio_path)
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
    
    # Create entities directory if it doesn't exist
    entities_dir = Path("backend/app/entities")
    entities_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename based on input files and UUID
    unique_id = str(uuid.uuid4())[:8]  # Use first 8 characters of UUID for shorter IDs
    if audio_path and document_path:
        filename = f"combined_audio_and_document_{unique_id}.txt"
    elif audio_path:
        filename = f"audio_transcription_{unique_id}.txt"
    else:
        filename = f"document_text_{unique_id}.txt"
    
    # Save combined text to file
    output_file = files_dir / filename
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_text)
    
    # Extract entities and concepts
    try:
        entities = await extract_entities_and_concepts(final_text)
        
        # First save the entities file
        entities_file = entities_dir / f"entities_{unique_id}.json"
        with open(entities_file, "w", encoding="utf-8") as f:
            json.dump(entities, f, indent=2, ensure_ascii=False)
        print(f"Entities saved to: {entities_file}")
        
        # Extract relationships using OpenAI API
        relationships = await extract_relationships(entities)
        unique_nodes = set()
        for edge in relationships:
            unique_nodes.add(edge['source'])
            unique_nodes.add(edge['target'])
        
        # Create node-to-id mapping
        node_to_id = {node: str(idx + 1) for idx, node in enumerate(unique_nodes)}
        
        # Save node-to-id mapping
        node_mapping_file = entities_dir / f"node_mapping_{unique_id}.json"
        with open(node_mapping_file, "w", encoding="utf-8") as f:
            json.dump(node_to_id, f, indent=2, ensure_ascii=False)
        print(f"Node mapping saved to: {node_mapping_file}")
        
        # Format edges with numeric IDs
        formatted_edges = []
        for edge in relationships:
            source_id = node_to_id[edge['source']]
            target_id = node_to_id[edge['target']]
            edge_id = f"{source_id}-{target_id}"
            formatted_edges.append({
                "source": source_id,
                "target": target_id,
                "id": edge_id,
                "label": edge['relation']
            })
        
        # Save relationships to a separate file
        relationships_file = entities_dir / f"relationships_{unique_id}.json"
        with open(relationships_file, "w", encoding="utf-8") as f:
            json.dump(formatted_edges, f, indent=2, ensure_ascii=False)
        print(f"Relationships saved to: {relationships_file}")
        
    except Exception as e:
        print(f"Error extracting entities and relationships: {e}")
    
    return str(output_file) 