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
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(project_root))

from v1.src.external.retriever import setup_rag, set_rag_retriever, get_rag_retriever, get_relevant_context
# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

router = APIRouter()

@router.get("/node_context/{node_label}")
async def get_node_context(node_label: str):
    """
    Get relevant context for a node using RAG.
    """
    try:
        print("\n=== Node Context Request Debug ===")
        print(f"Requested node label: {node_label}")
        
        retriever = get_rag_retriever()
        if not retriever:
            print("❌ Error: RAG retriever is not initialized")
            raise HTTPException(
                status_code=404, 
                detail="RAG system not initialized. Please upload and process files first."
            )
        
        print("✅ Retriever found, getting context...")
        # Get context for the node label
        context = get_relevant_context(node_label)
        
        if not context:
            print("❌ No context found for node")
            return {"context": "No relevant context found for this node."}
            
        print("\n=== Retrieved Context ===")
        print(context)
        print("\n=== End Context ===\n")
        
        return {"context": context}
    except HTTPException as he:
        print(f"❌ HTTP Exception in get_node_context: {str(he)}")
        raise he
    except Exception as e:
        print(f"❌ Unexpected error in get_node_context: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving context: {str(e)}"
        )

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
    if not entities:
        print("Warning: No entities provided to extract relationships")
        return []
        
    # Convert entities to a format suitable for the API
    entities_text = "\n".join([
        f"{entity}: {desc['description'] if isinstance(desc, dict) else desc}"
        for entity, desc in entities.items()
    ])
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4",  # Changed from gpt-4o-mini to gpt-4
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
        print(f"Raw API response: {response_text}")  # Debug log
        
        try:
            # Try to find JSON in the response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                relationships = json.loads(response_text[json_start:json_end])
                print(f"Found {len(relationships)} relationships")
                return relationships
            else:
                print("Warning: No JSON array found in response")
                return []
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
        filename = f"combined_audio_and_document.txt"
    elif audio_path:
        filename = f"audio_transcription.txt"
    else:
        filename = f"document_text.txt"
    
    # Save combined text to file
    output_file = files_dir / filename
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_text)
    
    # Set up RAG with the combined text file
    try:
        print("\n=== RAG Setup Debug ===")
        print("Setting up RAG system...")
        print(f"Using file: {output_file}")
        
        # Verify file exists and has content
        if not output_file.exists():
            print("❌ Error: Output file does not exist")
            raise ValueError("Output file not found")
            
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                print("❌ Error: Output file is empty")
                raise ValueError("Output file is empty")
            print(f"File size: {len(content)} characters")
        
        print("Creating RAG retriever...")
        retriever = setup_rag([str(output_file)])
        
        if retriever:
            print("✅ RAG retriever created successfully")
            print("Setting global retriever...")
            set_rag_retriever(retriever)
            print("✅ RAG system set up successfully")
            
            # Verify retriever is set
            global_retriever = get_rag_retriever()
            if global_retriever:
                print("✅ Global retriever verified")
            else:
                print("❌ Warning: Global retriever not set properly")
        else:
            print("❌ Warning: Failed to create RAG retriever")
            
        print("=== End RAG Setup Debug ===\n")
    except Exception as e:
        print(f"❌ Error setting up RAG system: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    # Extract entities and concepts
    try:
        entities = await extract_entities_and_concepts(final_text)
        if not entities:
            print("Warning: No entities were extracted from the text")
            return str(output_file)
            
        print(f"Extracted {len(entities)} entities")  # Debug log
        
        # First save the entities file
        entities_file = entities_dir / f"entities_{unique_id}.json"
        with open(entities_file, "w", encoding="utf-8") as f:
            json.dump(entities, f, indent=2, ensure_ascii=False)
        print(f"Entities saved to: {entities_file}")
        
        # Extract relationships using OpenAI API
        relationships = await extract_relationships(entities)
        
        # Create nodes from all entities first
        all_nodes = list(entities.keys())
        node_to_id = {node: str(idx + 1) for idx, node in enumerate(all_nodes)}
        
        # Debug log the available nodes
        print(f"Available nodes: {all_nodes}")
        
        # Create nodes array with all entities
        nodes = [
            {"id": node_to_id[node], "label": node}
            for node in all_nodes
        ]
        
        # Save nodes file
        nodes_file = entities_dir / f"nodes.json"
        with open(nodes_file, "w", encoding="utf-8") as f:
            json.dump(nodes, f, indent=2, ensure_ascii=False)
        print(f"Nodes saved to: {nodes_file}")
        
        if not relationships:
            print("Warning: No relationships were extracted")
            # Save empty relationships file
            relationships_file = entities_dir / f"relationships.json"
            with open(relationships_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            print(f"Empty relationships saved to: {relationships_file}")
            return str(output_file)
            
        # Format edges with numeric IDs
        formatted_edges = []
        for edge in relationships:
            try:
                source = edge['source']
                target = edge['target']
                
                # Debug log the edge being processed
                print(f"Processing edge: {source} -> {target}")
                
                if source not in node_to_id:
                    print(f"Warning: Source entity '{source}' not found in nodes")
                    continue
                if target not in node_to_id:
                    print(f"Warning: Target entity '{target}' not found in nodes")
                    continue
                    
                source_id = node_to_id[source]
                target_id = node_to_id[target]
                edge_id = f"{source_id}-{target_id}"
                formatted_edges.append({
                    "source": source_id,
                    "target": target_id,
                    "id": edge_id,
                    "label": edge['relation']
                })
            except KeyError as e:
                print(f"Warning: Missing required field in edge: {e}")
                continue
            except Exception as e:
                print(f"Warning: Error processing edge: {e}")
                continue
        
        # Save relationships to a separate file
        relationships_file = entities_dir / f"relationships.json"
        with open(relationships_file, "w", encoding="utf-8") as f:
            json.dump(formatted_edges, f, indent=2, ensure_ascii=False)
        print(f"Relationships saved to: {relationships_file}")
        print(f"Successfully processed {len(formatted_edges)} relationships out of {len(relationships)} total")
        
    except Exception as e:
        print(f"Error extracting entities and relationships: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")  # Print full traceback
    
    return str(output_file) 