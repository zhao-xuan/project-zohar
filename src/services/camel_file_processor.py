#!/usr/bin/env python3
"""
Camel-AI File Processing System

A battle-tested system for turning mixed folders into schema-aware vector knowledge-bases
using Camel-AI's ecosystem of loaders, toolkits, and storage adapters.
"""

import asyncio
import json
import logging
import magic
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

# Camel-AI Core Imports - simplified to avoid unstructured dependency
try:
    from camel.storages.vectordb_storages.chroma import ChromaStorage
    from camel.embeddings import OpenAIEmbeddings
    from camel.retrievals import AutoRetriever, RetrievalToolkit
    from camel.utils.chunker import uio_chunker
    from camel.agents import ChatAgent
    from camel.messages import BaseMessage
    from camel.types import TaskType, RoleType
    from camel.configs import ChatGPTConfig
    CAMEL_CORE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Camel-AI core components not available: {e}")
    CAMEL_CORE_AVAILABLE = False

# Try to import optional loaders and toolkits
try:
    from camel.loaders import MarkItDownLoader
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False
    logger.warning("MarkItDownLoader not available")

try:
    from camel.toolkits import ImageAnalysisToolkit, AudioAnalysisToolkit
    TOOLKITS_AVAILABLE = True
except ImportError:
    TOOLKITS_AVAILABLE = False
    logger.warning("Camel-AI toolkits not available - image/audio processing disabled")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global flags for optional dependencies
UNSTRUCTURED_AVAILABLE = False
TOOLKITS_AVAILABLE = False

@dataclass
class ProcessedFile:
    """Structure for processed file information"""
    file_path: str
    file_name: str
    file_extension: str
    file_size: int
    mime_type: str
    content_type: str  # 'text', 'image', 'audio', 'video', 'binary', 'unknown'
    processed_content: str
    metadata: Dict[str, Any]
    chunks: List[Dict[str, Any]]
    schema_collection: str
    processing_timestamp: str
    content_hash: str

@dataclass
class CollectionSchema:
    """Schema definition for vector collections"""
    collection_name: str
    description: str
    fields: Dict[str, str]
    extra_fields: Dict[str, Any]
    embedding_model: str
    created_at: str

class SchemaDesignerAgent:
    """Agent responsible for designing vector database schemas"""
    
    def __init__(self, model_config: ChatGPTConfig = None):
        self.model_config = model_config or ChatGPTConfig()
        self.agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Schema Designer",
                content="You are a database schema designer. Given sample metadata, output a JSON schema optimized for vector similarity search and filtering."
            ),
            model_config=self.model_config,
            task_type=TaskType.CHATBOT
        )
    
    async def design_schema(self, sample_metadata: List[Dict[str, Any]], collection_name: str) -> CollectionSchema:
        """Design a schema based on sample metadata"""
        try:
            prompt = f"""
            Analyze the following sample metadata and design an optimal ChromaDB schema:
            
            Collection: {collection_name}
            Sample Metadata: {json.dumps(sample_metadata[:5], indent=2)}
            
            Generate a JSON response with:
            {{
                "collection_name": "{collection_name}",
                "description": "Brief description of what this collection stores",
                "fields": {{"field_name": "field_type"}},
                "extra_fields": {{"modality_specific_field": "description"}},
                "indexing_strategy": ["field1", "field2"]
            }}
            """
            
            response = self.agent.step(BaseMessage.make_user_message(
                role_name="User",
                content=prompt
            ))
            
            try:
                schema_data = json.loads(response.msg.content)
                return CollectionSchema(
                    collection_name=schema_data["collection_name"],
                    description=schema_data["description"],
                    fields=schema_data["fields"],
                    extra_fields=schema_data.get("extra_fields", {}),
                    embedding_model="openai",
                    created_at=datetime.now().isoformat()
                )
            except json.JSONDecodeError:
                # Fallback schema
                return self._create_fallback_schema(collection_name)
                
        except Exception as e:
            logger.error(f"Error designing schema: {e}")
            return self._create_fallback_schema(collection_name)
    
    def _create_fallback_schema(self, collection_name: str) -> CollectionSchema:
        """Create a fallback schema when AI generation fails"""
        return CollectionSchema(
            collection_name=collection_name,
            description=f"Auto-generated schema for {collection_name}",
            fields={
                "id": "string",
                "embedding": "vector",
                "content": "text",
                "path": "string",
                "media_type": "string",
                "size": "integer",
                "mtime": "timestamp"
            },
            extra_fields={},
            embedding_model="openai",
            created_at=datetime.now().isoformat()
        )

class FileSummarizerAgent:
    """Agent responsible for summarizing collections and files"""
    
    def __init__(self, model_config: ChatGPTConfig = None):
        self.model_config = model_config or ChatGPTConfig()
        self.agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="File Summarizer",
                content="You are a file summarizer. Provide concise 1-2 sentence descriptions of file collections for retrieval routing."
            ),
            model_config=self.model_config,
            task_type=TaskType.CHATBOT
        )
    
    async def summarize_collection(self, collection_name: str, sample_files: List[ProcessedFile]) -> str:
        """Generate a summary description for a collection"""
        try:
            prompt = f"""
            Summarize this collection in 1-2 sentences for query routing:
            
            Collection: {collection_name}
            File Count: {len(sample_files)}
            Sample Files: {[f.file_name for f in sample_files[:5]]}
            Content Types: {list(set(f.content_type for f in sample_files))}
            
            Provide a concise description that helps determine when to query this collection.
            """
            
            response = self.agent.step(BaseMessage.make_user_message(
                role_name="User",
                content=prompt
            ))
            
            return response.msg.content.strip()
            
        except Exception as e:
            logger.error(f"Error summarizing collection: {e}")
            return f"Collection containing {len(sample_files)} files of various types"

class CamelFileProcessor:
    """
    Main file processor using Camel-AI ecosystem
    """
    
    def __init__(self, 
                 storage_path: str = "data/camel_vector_db",
                 embedding_model: str = "text-embedding-ada-002",
                 chunk_size: int = 512,
                 chunk_overlap: int = 50):
        """
        Initialize the Camel-AI file processor
        
        Args:
            storage_path: Path for vector database storage
            embedding_model: OpenAI embedding model to use
            chunk_size: Size of text chunks for embedding
            chunk_overlap: Overlap between chunks
        """
        if not CAMEL_CORE_AVAILABLE:
            raise ImportError("Camel-AI core components are not available. Please install camel-ai.")
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        
        # Initialize vector storage
        self.vector_store = ChromaStorage(
            path=str(self.storage_path),
            embedding_model=self.embeddings
        )
        
        # Initialize toolkits (if available)
        self.image_toolkit = ImageAnalysisToolkit() if TOOLKITS_AVAILABLE else None
        self.audio_toolkit = AudioAnalysisToolkit() if TOOLKITS_AVAILABLE else None
        
        # Initialize agents
        self.schema_designer = SchemaDesignerAgent()
        self.file_summarizer = FileSummarizerAgent()
        
        # Initialize retrieval components
        self.auto_retriever = None
        self.retrieval_toolkit = None
        
        # Processing configuration
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Storage for schemas and registry
        self.collection_schemas = {}
        self.collection_registry = {}
        
        # Statistics
        self.processing_stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'collections_created': 0,
            'total_chunks': 0
        }
    
    async def process_directory(self, directory_path: str, 
                              include_patterns: List[str] = None,
                              exclude_patterns: List[str] = None) -> Dict[str, Any]:
        """
        Main method to process a directory and create vector knowledge base
        
        Args:
            directory_path: Path to directory to process
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude
            
        Returns:
            Processing results and statistics
        """
        logger.info(f"Starting Camel-AI processing of directory: {directory_path}")
        
        try:
            # Step 1: Discovery - fingerprint all files
            logger.info("Step 1: File discovery and fingerprinting...")
            discovered_files = await self._discover_files(directory_path, include_patterns, exclude_patterns)
            
            # Step 2: Normalization - route to correct processors
            logger.info("Step 2: Content normalization...")
            processed_files = await self._normalize_content(discovered_files)
            
            # Step 3: Description & chunking - create summaries and chunks
            logger.info("Step 3: Content description and chunking...")
            chunked_files = await self._describe_and_chunk(processed_files)
            
            # Step 4: Schema generation - design collections
            logger.info("Step 4: Dynamic schema generation...")
            await self._generate_schemas(chunked_files)
            
            # Step 5: Embedding & storage - store in vector database
            logger.info("Step 5: Embedding and storage...")
            storage_results = await self._embed_and_store(chunked_files)
            
            # Step 6: Collection summarization - create registry
            logger.info("Step 6: Collection summarization...")
            await self._summarize_collections()
            
            # Step 7: Retrieval setup - configure AutoRetriever
            logger.info("Step 7: Retrieval system setup...")
            await self._setup_retrieval()
            
            return {
                'success': True,
                'processing_stats': self.processing_stats,
                'collections_created': list(self.collection_schemas.keys()),
                'collection_registry': self.collection_registry,
                'storage_results': storage_results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in directory processing: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_stats': self.processing_stats,
                'timestamp': datetime.now().isoformat()
            }
    
    async def _discover_files(self, directory_path: str, 
                            include_patterns: List[str] = None,
                            exclude_patterns: List[str] = None) -> List[Dict[str, Any]]:
        """Step 1: Discover and fingerprint files"""
        discovered_files = []
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory does not exist: {directory_path}")
        
        # Walk through all files
        for file_path in directory_path.rglob('*'):
            if file_path.is_file():
                self.processing_stats['total_files'] += 1
                
                try:
                    # Apply include/exclude patterns
                    if include_patterns and not any(file_path.match(pattern) for pattern in include_patterns):
                        continue
                    
                    if exclude_patterns and any(file_path.match(pattern) for pattern in exclude_patterns):
                        continue
                    
                    # Get file fingerprint
                    file_info = await self._fingerprint_file(file_path)
                    discovered_files.append(file_info)
                    
                except Exception as e:
                    logger.error(f"Error discovering file {file_path}: {e}")
                    self.processing_stats['failed_files'] += 1
        
        logger.info(f"Discovered {len(discovered_files)} files for processing")
        return discovered_files
    
    async def _fingerprint_file(self, file_path: Path) -> Dict[str, Any]:
        """Fingerprint a file using python-magic and basic analysis"""
        try:
            # Get MIME type
            mime_type = magic.from_file(str(file_path), mime=True)
            
            # Get file stats
            stat = file_path.stat()
            
            # Generate content hash
            with open(file_path, 'rb') as f:
                content_hash = hashlib.md5(f.read()).hexdigest()
            
            return {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'file_extension': file_path.suffix.lower(),
                'file_size': stat.st_size,
                'mime_type': mime_type,
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'content_hash': content_hash
            }
            
        except Exception as e:
            logger.error(f"Error fingerprinting file {file_path}: {e}")
            return {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'error': str(e)
            }
    
    async def _normalize_content(self, discovered_files: List[Dict[str, Any]]) -> List[ProcessedFile]:
        """Step 2: Normalize content using appropriate loaders and toolkits"""
        processed_files = []
        
        for file_info in discovered_files:
            try:
                file_path = Path(file_info['file_path'])
                mime_type = file_info.get('mime_type', 'application/octet-stream')
                
                # Route to appropriate processor
                if mime_type.startswith("text/") or file_path.suffix in {".pdf", ".html", ".md", ".txt"}:
                    processed_content = await self._process_text_file(file_path, mime_type)
                elif mime_type.startswith("image/"):
                    processed_content = await self._process_image_file(file_path)
                elif mime_type.startswith("audio/"):
                    processed_content = await self._process_audio_file(file_path)
                elif file_path.suffix in {".docx", ".doc"}:
                    processed_content = await self._process_office_file(file_path)
                else:
                    processed_content = await self._process_binary_file(file_path, mime_type)
                
                # Create ProcessedFile object
                processed_file = ProcessedFile(
                    file_path=str(file_path),
                    file_name=file_path.name,
                    file_extension=file_path.suffix.lower(),
                    file_size=file_info.get('file_size', 0),
                    mime_type=mime_type,
                    content_type=processed_content['content_type'],
                    processed_content=processed_content['content'],
                    metadata=processed_content['metadata'],
                    chunks=[],  # Will be filled in next step
                    schema_collection=self._determine_collection_name(file_path, mime_type),
                    processing_timestamp=datetime.now().isoformat(),
                    content_hash=file_info.get('content_hash', '')
                )
                
                processed_files.append(processed_file)
                self.processing_stats['processed_files'] += 1
                
            except Exception as e:
                logger.error(f"Error normalizing file {file_info.get('file_path', 'unknown')}: {e}")
                self.processing_stats['failed_files'] += 1
        
        return processed_files
    
    async def _process_text_file(self, file_path: Path, mime_type: str) -> Dict[str, Any]:
        """Process text-based files using available loaders"""
        try:
            if file_path.suffix == '.pdf':
                # Use fallback PDF reader
                content = await self._fallback_pdf_reader(file_path)
            elif file_path.suffix in {'.html', '.htm'}:
                # Try MarkItDownLoader for HTML, fallback to basic reading
                if MARKITDOWN_AVAILABLE:
                    try:
                        loader = MarkItDownLoader()
                        content = loader.load(str(file_path))
                    except Exception:
                        content = await self._fallback_text_reader(file_path)
                else:
                    content = await self._fallback_text_reader(file_path)
            else:
                # Use basic file reading for other text files
                content = await self._fallback_text_reader(file_path)
            
            return {
                'content_type': 'text',
                'content': content,
                'metadata': {
                    'loader_type': type(loader).__name__,
                    'file_type': 'text',
                    'char_count': len(content),
                    'line_count': content.count('\n') + 1
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {e}")
            return {
                'content_type': 'error',
                'content': f"Error processing text file: {e}",
                'metadata': {'error': str(e)}
            }
    
    async def _process_image_file(self, file_path: Path) -> Dict[str, Any]:
        """Process image files using ImageAnalysisToolkit"""
        try:
            # Generate image caption if toolkit available
            if self.image_toolkit:
                caption = self.image_toolkit.image_to_text(str(file_path))
            else:
                caption = f"Image file: {file_path.name}"
            
            # Get image dimensions and other metadata
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    width, height = img.size
                    format_type = img.format
                    mode = img.mode
            except ImportError:
                width, height = 0, 0
                format_type, mode = "unknown", "unknown"
            
            return {
                'content_type': 'image',
                'content': caption,
                'metadata': {
                    'image_width': width,
                    'image_height': height,
                    'image_format': format_type,
                    'image_mode': mode,
                    'caption': caption,
                    'toolkit_available': self.image_toolkit is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing image file {file_path}: {e}")
            return {
                'content_type': 'error',
                'content': f"Error processing image: {e}",
                'metadata': {'error': str(e)}
            }
    
    async def _process_audio_file(self, file_path: Path) -> Dict[str, Any]:
        """Process audio files using AudioAnalysisToolkit"""
        try:
            # Transcribe audio if toolkit available
            if self.audio_toolkit:
                transcript = self.audio_toolkit.transcribe(str(file_path))
            else:
                transcript = f"Audio file: {file_path.name} (transcription unavailable)"
            
            return {
                'content_type': 'audio',
                'content': transcript,
                'metadata': {
                    'transcription': transcript,
                    'audio_file': str(file_path),
                    'toolkit_available': self.audio_toolkit is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing audio file {file_path}: {e}")
            return {
                'content_type': 'error',
                'content': f"Error processing audio: {e}",
                'metadata': {'error': str(e)}
            }
    
    async def _process_office_file(self, file_path: Path) -> Dict[str, Any]:
        """Process office files using MarkItDownLoader"""
        try:
            loader = MarkItDownLoader()
            content = loader.load(str(file_path))
            
            return {
                'content_type': 'text',
                'content': content,
                'metadata': {
                    'loader_type': 'MarkItDownLoader',
                    'file_type': 'office',
                    'original_format': file_path.suffix
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing office file {file_path}: {e}")
            return {
                'content_type': 'error',
                'content': f"Error processing office file: {e}",
                'metadata': {'error': str(e)}
            }
    
    async def _process_binary_file(self, file_path: Path, mime_type: str) -> Dict[str, Any]:
        """Process binary files with basic metadata"""
        try:
            content = f"Binary file {file_path.name} ({mime_type}), {file_path.stat().st_size} bytes."
            
            return {
                'content_type': 'binary',
                'content': content,
                'metadata': {
                    'file_type': 'binary',
                    'mime_type': mime_type,
                    'processing_note': 'Binary file - basic metadata only'
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing binary file {file_path}: {e}")
            return {
                'content_type': 'error',
                'content': f"Error processing binary file: {e}",
                'metadata': {'error': str(e)}
            }
    
    def _determine_collection_name(self, file_path: Path, mime_type: str) -> str:
        """Determine the appropriate collection name for a file"""
        # Use parent directory name as collection base
        parent_dir = file_path.parent.name
        
        # Add content type suffix
        if mime_type.startswith('text/') or file_path.suffix in {'.txt', '.md', '.html'}:
            return f"{parent_dir}_texts"
        elif mime_type.startswith('image/'):
            return f"{parent_dir}_images"
        elif mime_type.startswith('audio/'):
            return f"{parent_dir}_audio"
        elif 'chat' in file_path.name.lower() or 'message' in file_path.name.lower():
            return f"{parent_dir}_chats"
        else:
            return f"{parent_dir}_documents"
    
    async def _describe_and_chunk(self, processed_files: List[ProcessedFile]) -> List[ProcessedFile]:
        """Step 3: Create human-level summaries and token-sized chunks"""
        for processed_file in processed_files:
            try:
                if processed_file.content_type in ['text', 'image', 'audio'] and processed_file.processed_content:
                    # Create chunks using Camel's chunker
                    chunks = uio_chunker(
                        processed_file.processed_content,
                        chunk_size=self.chunk_size,
                        overlap=self.chunk_overlap
                    )
                    
                    # Convert chunks to dictionaries with metadata
                    processed_file.chunks = []
                    for i, chunk in enumerate(chunks):
                        chunk_data = {
                            'chunk_id': f"{processed_file.content_hash}_{i}",
                            'chunk_index': i,
                            'text': chunk.text,
                            'metadata': {
                                'file_path': processed_file.file_path,
                                'file_name': processed_file.file_name,
                                'content_type': processed_file.content_type,
                                'chunk_size': len(chunk.text),
                                **processed_file.metadata
                            }
                        }
                        processed_file.chunks.append(chunk_data)
                        self.processing_stats['total_chunks'] += 1
                
            except Exception as e:
                logger.error(f"Error chunking file {processed_file.file_name}: {e}")
        
        return processed_files
    
    async def _generate_schemas(self, processed_files: List[ProcessedFile]) -> None:
        """Step 4: Generate dynamic schemas for collections"""
        # Group files by collection
        collections = {}
        for file in processed_files:
            collection_name = file.schema_collection
            if collection_name not in collections:
                collections[collection_name] = []
            collections[collection_name].append(file)
        
        # Generate schema for each collection
        for collection_name, files in collections.items():
            try:
                # Sample metadata from files
                sample_metadata = [file.metadata for file in files[:5]]
                
                # Generate schema
                schema = await self.schema_designer.design_schema(sample_metadata, collection_name)
                self.collection_schemas[collection_name] = schema
                
                # Create collection in vector store
                await self._create_collection(schema)
                self.processing_stats['collections_created'] += 1
                
                logger.info(f"Created collection: {collection_name}")
                
            except Exception as e:
                logger.error(f"Error generating schema for collection {collection_name}: {e}")
    
    async def _create_collection(self, schema: CollectionSchema) -> None:
        """Create a collection in the vector store"""
        try:
            # Create collection with schema
            self.vector_store.create_collection(
                collection_name=schema.collection_name,
                schema=schema.fields
            )
            
        except Exception as e:
            logger.error(f"Error creating collection {schema.collection_name}: {e}")
    
    async def _embed_and_store(self, processed_files: List[ProcessedFile]) -> Dict[str, Any]:
        """Step 5: Embed and store documents in vector database"""
        storage_results = {}
        
        # Group files by collection
        collections = {}
        for file in processed_files:
            collection_name = file.schema_collection
            if collection_name not in collections:
                collections[collection_name] = []
            collections[collection_name].append(file)
        
        # Store documents in each collection
        for collection_name, files in collections.items():
            try:
                documents = []
                metadatas = []
                
                for file in files:
                    for chunk in file.chunks:
                        documents.append(chunk['text'])
                        metadatas.append(chunk['metadata'])
                
                if documents:
                    # Add documents to collection
                    self.vector_store.add_documents(
                        collection_name=collection_name,
                        contents=documents,
                        metadatas=metadatas
                    )
                    
                    storage_results[collection_name] = {
                        'documents_stored': len(documents),
                        'files_processed': len(files)
                    }
                    
                    logger.info(f"Stored {len(documents)} documents in collection {collection_name}")
                
            except Exception as e:
                logger.error(f"Error storing documents in collection {collection_name}: {e}")
                storage_results[collection_name] = {'error': str(e)}
        
        return storage_results
    
    async def _summarize_collections(self) -> None:
        """Step 6: Create collection summaries for routing"""
        # Group processed files by collection for summarization
        collections = {}
        for collection_name in self.collection_schemas.keys():
            # Get sample files for this collection
            sample_files = []  # This would be populated from processed files
            
            try:
                summary = await self.file_summarizer.summarize_collection(collection_name, sample_files)
                self.collection_registry[collection_name] = {
                    'description': summary,
                    'schema': asdict(self.collection_schemas[collection_name]),
                    'created_at': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error summarizing collection {collection_name}: {e}")
                self.collection_registry[collection_name] = {
                    'description': f"Collection {collection_name}",
                    'error': str(e)
                }
    
    async def _setup_retrieval(self) -> None:
        """Step 7: Setup AutoRetriever and RetrievalToolkit"""
        try:
            # Create retrieval toolkit
            self.retrieval_toolkit = RetrievalToolkit(
                vector_storage=self.vector_store
            )
            
            # Setup AutoRetriever with collection registry
            self.auto_retriever = AutoRetriever(
                vector_storage=self.vector_store,
                collection_descriptions=self.collection_registry
            )
            
            logger.info("Retrieval system setup complete")
            
        except Exception as e:
            logger.error(f"Error setting up retrieval system: {e}")
    
    async def query(self, query: str, collection_name: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query the vector database"""
        try:
            if collection_name:
                # Query specific collection
                results = self.vector_store.query(
                    collection_name=collection_name,
                    query_texts=[query],
                    n_results=top_k
                )
            else:
                # Use AutoRetriever to choose best collection
                if self.auto_retriever:
                    results = await self.auto_retriever.retrieve(query, top_k=top_k)
                else:
                    # Fallback: query all collections
                    results = []
                    for collection_name in self.collection_schemas.keys():
                        collection_results = self.vector_store.query(
                            collection_name=collection_name,
                            query_texts=[query],
                            n_results=top_k
                        )
                        results.extend(collection_results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying vector database: {e}")
            return []
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about all collections"""
        return {
            'collections': list(self.collection_schemas.keys()),
            'registry': self.collection_registry,
            'schemas': {name: asdict(schema) for name, schema in self.collection_schemas.items()},
            'stats': self.processing_stats
        }
    
    async def save_processing_results(self, output_path: str) -> None:
        """Save processing results to file"""
        try:
            results = {
                'processing_stats': self.processing_stats,
                'collection_schemas': {name: asdict(schema) for name, schema in self.collection_schemas.items()},
                'collection_registry': self.collection_registry,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Processing results saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving processing results: {e}")
    
    async def _fallback_pdf_reader(self, file_path: Path) -> str:
        """Fallback PDF reader when UnstructuredIO is not available"""
        try:
            import pypdf
            with open(file_path, 'rb') as file:
                reader = pypdf.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except ImportError:
            return f"PDF file: {file_path.name} (PDF processing unavailable - install pypdf)"
        except Exception as e:
            return f"PDF file: {file_path.name} (error reading: {e})"
    
    async def _fallback_text_reader(self, file_path: Path) -> str:
        """Fallback text reader for basic file reading"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"Text file: {file_path.name} (error reading: {e})"

# Example usage and CLI interface
async def main():
    """Main function to demonstrate the Camel-AI file processor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Camel-AI File Processor")
    parser.add_argument("directory", help="Directory to process")
    parser.add_argument("-o", "--output", default="camel_processing_results.json", help="Output JSON file")
    parser.add_argument("--storage-path", default="data/camel_vector_db", help="Vector database storage path")
    parser.add_argument("--chunk-size", type=int, default=512, help="Chunk size for text splitting")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize processor
    processor = CamelFileProcessor(
        storage_path=args.storage_path,
        chunk_size=args.chunk_size
    )
    
    # Process directory
    results = await processor.process_directory(args.directory)
    
    # Save results
    await processor.save_processing_results(args.output)
    
    # Print summary
    print(f"\nProcessing completed!")
    print(f"Success: {results['success']}")
    if results['success']:
        stats = results['processing_stats']
        print(f"Total files: {stats['total_files']}")
        print(f"Processed files: {stats['processed_files']}")
        print(f"Failed files: {stats['failed_files']}")
        print(f"Collections created: {stats['collections_created']}")
        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Collections: {', '.join(results['collections_created'])}")

if __name__ == "__main__":
    asyncio.run(main())