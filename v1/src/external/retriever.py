from typing import List
from pathlib import Path
import hashlib
import pickle


from langchain_community.document_loaders import PyPDFLoader, PDFPlumberLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryStore
from langchain_core.documents import Document

_global_retriever = None

def get_cache_dir():
    """Get the cache directory, cretae if doesnt exist"""
    cache_dir = Path("cache/rag")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
def compute_files_hash(file_paths: List[str]) -> str:
    """compute hash of the files contents and paths to use as cache key"""
    hasher = hashlib.sha256()
    for file_path in sorted(file_paths):
        try:
            hasher.update(file_path.encode())
            with open(file_path, 'rb') as f:
                #chunck
                for chunk in iter(lambda: f.read(4096),b''):
                    hasher.update(chunk)
        except Exception as e:
            hasher.update(str(e).encode())
    return hasher.hexdigest

def save_rag_cache(file_paths: List[str], vector_store, doc_store):
    """ Save RAG components to cache."""
    try:
        cache_dir = get_cache_dir()
        files_hash = compute_files_hash(file_paths)
        vector_store.save_local(str(cache_dir / f"{files_hash}_vectors"))
        with open(cache_dir/f"{files_hash}_docstore.pkl", 'wb') as f: #maps document identifiers - to original content 
            pickle.dump(doc_store,f)
        with open(cache_dir/ f"{files_hash}_files.text", 'w') as f:
            f.write("\n".join(file_paths))
    except Exception as e:
        print(f"Error saving RAG cache: {e}")


def load_rag_cache(file_paths: List[str]) -> tuple:
    try:
        cache_dir = get_cache_dir()
        files_hash = compute_files_hash(file_paths)

        vector_path = cache_dir / f"{files_hash}_vectors"
        docstore_path = cache_dir / f"{files_hash}_docstore.pkl"
        files_path = cache_dir / f"{files_hash}_files.txt"

        #check if cache exists
        if not (vector_path.exists() and docstore_path.exists() and file_paths.exist()):
            return None, None 


        #validate file paths havent changed

        with open(files_path, 'r') as f:
            cached_files= f.read().splitlines()
        if set(cached_files) != set(file_paths): #removes duplicates 
            return None, None

        #load vector store
        embeddings = OpenAIEmbeddings(model="text-embedding_ada-002")
        vector_store = FAISS.load_local(str(vector_path), embeddings)

        #load document store with safety flag 
        with open(docstore_path, 'rb') as f:
            doc_store = pickle.load(f, fix_imports=True, encoding='latin1')
        return vector_store, doc_store
    except Exception as e:
        print(f"Error Loading RAG cache: {e}")
        return None,None
    

#meat of the RAG system
def setup_rag(file_paths: List[str]):
    """Set up RAG system with caching"""

    vector_store, doc_store = load_rag_cache(file_paths)

    #if the vector store exists
    if vector_store is not None and doc_store is not None:
        retriever = ParentDocumentRetriever(
            vectorstore=vector_store,
            docstore=doc_store,
            child_splitter=RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=0,
                separators=["course:"],
            ),
            parent_splitter=RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=500,
                separators=["\n\n", "\n", ".", "!", "?", ";"],
            ),
            search_kwargs={"k": 4},
        )
        return retriever
    #set up if no cache
    child_splitter=RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=0,
        separators=["course:"],
    )
    parent_splitter=RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=500,
        separators=["\n\n", "\n", ".", "!", "?", ";"],
    )
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
    vector_store = FAISS.from_texts(["placeholder"], embeddings)
    doc_store = InMemoryStore()

    retriever = ParentDocumentRetriever(
        vectorstore=vector_store,
        docstore=doc_store,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
        search_kwargs={"k":4},
    )

    all_docs = []
    for file_path in file_paths:
        try:
            loader = TextLoader(file_path, encoding='utf-8')
            docs = loader.load()

            cleaned_docs = []
            for doc in docs:
                cleaned_text = " ".join(doc.page_content.split())
                if len(cleaned_text.strip()) > 0:
                    cleaned_docs.append(Document(page_content=cleaned_text))
            all_docs.extend(cleaned_docs)
                    
        except Exception as e:
            print(f"Error Loading file: {e}")
    #set up rag 
    if all_docs:
        #add documents to retriever
        retriever.add_documents(all_docs)
        save_rag_cache(file_paths,vector_store,doc_store)
    
    return retriever

def get_rag_retriever():
    """Get the global RAG retriever instance"""
    global _global_retriever
    return _global_retriever


def set_rag_retriever(retriever):
    """Set the global RAG retriever instance"""
    global _global_retriever
    _global_retriever = retriever

def get_relevant_context(query: str, k: int =4) -> str:
    """Get relevant context from supplementary files using RAG"""
    global _global_retriever
    try:
        if not _global_retriever:
            print("Error: No RAG retriever available")
            return ""
            
        print(f"Invoking retriever with query: {query}")
        relevant_docs = _global_retriever.invoke(
            query,
            config={"search_kwargs": {"k": k, "score_threshold": 0.7}}
        )
        
        if not relevant_docs:
            print("No relevant documents found")
            return ""
            
        print(f"Found {len(relevant_docs)} relevant documents")
        relevant_docs = relevant_docs[:k]

        contexts = []
        for i,doc in enumerate(relevant_docs, 1):
            try:
                clean_text = " ".join(doc.page_content.split())
                contexts.append(f"[{i}]{clean_text}")
            except Exception as e:
                print(f"Error processing document {i}: {str(e)}")
                continue

        if not contexts:
            print("No valid contexts found after processing")
            return ""
            
        context = "\n\n".join(contexts)
        print("Successfully generated context")
        return context 
    except Exception as e:
        print(f"Error in get_relevant_context: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return ""




        




