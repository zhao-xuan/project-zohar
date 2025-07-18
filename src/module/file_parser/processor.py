"""
Data Processing for Project Zohar.

This module provides comprehensive data processing capabilities including
file analysis, parsing, vectorization, and intelligent document processing.
"""

import os
import json
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
import logging
import asyncio

# File processing imports
try:
    import docx
    from docx import Document
except ImportError:
    docx = None

try:
    import PyPDF2
    import pdfplumber
except ImportError:
    PyPDF2 = None
    pdfplumber = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

from zohar.config.settings import get_settings
from zohar.utils.logging import get_logger
from zohar.services.data_processing.vector_store import VectorStore
from zohar.services.privacy.privacy_filter import PrivacyFilter, PrivacyLevel

logger = get_logger(__name__)


class FileType:
    """Supported file types."""
    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    IMAGE = "image"
    MARKDOWN = "markdown"
    HTML = "html"
    EMAIL = "email"
    UNKNOWN = "unknown"


class DataProcessor:
    """
    Comprehensive data processing for various file formats.
    
    This class provides:
    - File type detection and parsing
    - Content extraction and analysis
    - Document vectorization
    - Privacy filtering and anonymization
    - Batch processing capabilities
    """
    
    def __init__(
        self,
        user_id: str,
        privacy_level: PrivacyLevel = PrivacyLevel.HIGH,
        vector_store: Optional[VectorStore] = None
    ):
        """
        Initialize the data processor.
        
        Args:
            user_id: Unique identifier for the user
            privacy_level: Privacy protection level
            vector_store: Vector store instance for document embedding
        """
        self.user_id = user_id
        self.settings = get_settings()
        
        # Initialize privacy filter
        self.privacy_filter = PrivacyFilter(privacy_level)
        
        # Initialize vector store
        self.vector_store = vector_store or VectorStore(user_id)
        
        # Processing statistics
        self.stats = {
            "files_processed": 0,
            "total_size": 0,
            "by_type": {},
            "errors": 0,
            "start_time": None
        }
        
        # File type mappings
        self.file_type_mappings = {
            ".txt": FileType.TEXT,
            ".pdf": FileType.PDF,
            ".docx": FileType.DOCX,
            ".doc": FileType.DOCX,
            ".xlsx": FileType.EXCEL,
            ".xls": FileType.EXCEL,
            ".csv": FileType.CSV,
            ".json": FileType.JSON,
            ".xml": FileType.XML,
            ".md": FileType.MARKDOWN,
            ".html": FileType.HTML,
            ".htm": FileType.HTML,
            ".png": FileType.IMAGE,
            ".jpg": FileType.IMAGE,
            ".jpeg": FileType.IMAGE,
            ".gif": FileType.IMAGE,
            ".bmp": FileType.IMAGE,
            ".tiff": FileType.IMAGE,
            ".eml": FileType.EMAIL,
            ".msg": FileType.EMAIL
        }
        
        logger.info(f"Data processor initialized for user {user_id}")
    
    async def initialize(self) -> bool:
        """
        Initialize the data processor.
        
        Returns:
            Success status
        """
        try:
            # Initialize vector store
            if not await self.vector_store.initialize():
                logger.error("Failed to initialize vector store")
                return False
            
            # Reset statistics
            self.stats = {
                "files_processed": 0,
                "total_size": 0,
                "by_type": {},
                "errors": 0,
                "start_time": datetime.now()
            }
            
            logger.info("Data processor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize data processor: {e}")
            return False
    
    async def process_file(
        self,
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a single file.
        
        Args:
            file_path: Path to the file to process
            metadata: Optional metadata to associate with the file
            
        Returns:
            Processing result dictionary
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Get file info
            file_info = self._get_file_info(file_path)
            
            # Detect file type
            file_type = self._detect_file_type(file_path)
            
            # Extract content
            content = await self._extract_content(file_path, file_type)
            
            # Process content
            processed_content = await self._process_content(content, file_info, metadata)
            
            # Update statistics
            self._update_stats(file_info, file_type)
            
            logger.info(f"Successfully processed file: {file_path.name}")
            
            return {
                "success": True,
                "file_path": str(file_path),
                "file_info": file_info,
                "file_type": file_type,
                "content": processed_content,
                "processed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            self.stats["errors"] += 1
            
            return {
                "success": False,
                "file_path": str(file_path),
                "error": str(e),
                "processed_at": datetime.now().isoformat()
            }
    
    async def process_directory(
        self,
        directory_path: Union[str, Path],
        recursive: bool = True,
        file_patterns: Optional[List[str]] = None,
        max_files: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process all files in a directory.
        
        Args:
            directory_path: Path to the directory
            recursive: Whether to process subdirectories
            file_patterns: List of file patterns to include
            max_files: Maximum number of files to process
            
        Returns:
            Batch processing results
        """
        try:
            directory_path = Path(directory_path)
            
            if not directory_path.exists():
                raise FileNotFoundError(f"Directory not found: {directory_path}")
            
            # Get list of files
            files = self._get_files_in_directory(
                directory_path, recursive, file_patterns, max_files
            )
            
            logger.info(f"Found {len(files)} files to process in {directory_path}")
            
            # Process files
            results = []
            for file_path in files:
                result = await self.process_file(file_path)
                results.append(result)
                
                # Add small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)
            
            # Calculate summary
            successful = sum(1 for r in results if r["success"])
            failed = len(results) - successful
            
            summary = {
                "total_files": len(files),
                "successful": successful,
                "failed": failed,
                "results": results,
                "processing_stats": self.get_processing_stats(),
                "processed_at": datetime.now().isoformat()
            }
            
            logger.info(f"Batch processing complete: {successful}/{len(files)} files processed successfully")
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to process directory {directory_path}: {e}")
            return {
                "total_files": 0,
                "successful": 0,
                "failed": 1,
                "error": str(e),
                "processed_at": datetime.now().isoformat()
            }
    
    async def analyze_content(
        self,
        content: str,
        content_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Analyze text content and extract insights.
        
        Args:
            content: Text content to analyze
            content_type: Type of content
            
        Returns:
            Content analysis results
        """
        try:
            # Basic text statistics
            word_count = len(content.split())
            char_count = len(content)
            line_count = content.count('\n') + 1
            
            # Privacy analysis
            privacy_summary = self.privacy_filter.get_privacy_summary(content)
            
            # Extract key information
            key_phrases = self._extract_key_phrases(content)
            entities = self._extract_entities(content)
            
            # Determine content classification
            classification = self._classify_content(content)
            
            # Generate summary
            summary = self._generate_summary(content)
            
            analysis = {
                "content_type": content_type,
                "statistics": {
                    "word_count": word_count,
                    "character_count": char_count,
                    "line_count": line_count,
                    "average_word_length": char_count / word_count if word_count > 0 else 0
                },
                "privacy_analysis": privacy_summary,
                "key_phrases": key_phrases,
                "entities": entities,
                "classification": classification,
                "summary": summary,
                "analyzed_at": datetime.now().isoformat()
            }
            
            logger.debug(f"Content analysis complete: {word_count} words, {len(key_phrases)} key phrases")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze content: {e}")
            return {"error": str(e), "analyzed_at": datetime.now().isoformat()}
    
    async def create_document_schema(
        self,
        content: str,
        file_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a schema for the document.
        
        Args:
            content: Document content
            file_info: File information
            
        Returns:
            Document schema
        """
        try:
            # Analyze content structure
            structure = self._analyze_document_structure(content)
            
            # Generate metadata schema
            metadata_schema = {
                "title": file_info.get("name", "Unknown"),
                "file_type": file_info.get("extension", ""),
                "size": file_info.get("size", 0),
                "created_at": file_info.get("created_at"),
                "modified_at": file_info.get("modified_at"),
                "content_type": structure.get("type", "text"),
                "language": structure.get("language", "en"),
                "sections": structure.get("sections", []),
                "tags": structure.get("tags", []),
                "privacy_level": self.privacy_filter.privacy_level.value
            }
            
            # Create schema
            schema = {
                "document_id": self._generate_document_id(content, file_info),
                "metadata": metadata_schema,
                "content_structure": structure,
                "processing_info": {
                    "processor_version": "1.0.0",
                    "processed_at": datetime.now().isoformat(),
                    "processing_time": 0  # Will be updated by caller
                },
                "schema_version": "1.0.0"
            }
            
            return schema
            
        except Exception as e:
            logger.error(f"Failed to create document schema: {e}")
            return {"error": str(e)}
    
    async def vectorize_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """
        Vectorize document content for search.
        
        Args:
            content: Document content
            metadata: Document metadata
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of document IDs in vector store
        """
        try:
            # Split content into chunks
            chunks = self._split_text_into_chunks(content, chunk_size, chunk_overlap)
            
            # Prepare metadata for each chunk
            chunk_metadatas = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_index": i,
                    "chunk_count": len(chunks),
                    "chunk_size": len(chunk),
                    "chunk_start": i * (chunk_size - chunk_overlap),
                    "vectorized_at": datetime.now().isoformat()
                })
                chunk_metadatas.append(chunk_metadata)
            
            # Add to vector store
            doc_ids = await self.vector_store.add_documents(
                documents=chunks,
                metadatas=chunk_metadatas
            )
            
            logger.info(f"Vectorized document into {len(chunks)} chunks")
            
            return doc_ids
            
        except Exception as e:
            logger.error(f"Failed to vectorize document: {e}")
            return []
    
    async def search_documents(
        self,
        query: str,
        limit: int = 10,
        file_types: Optional[List[str]] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search processed documents.
        
        Args:
            query: Search query
            limit: Maximum number of results
            file_types: Filter by file types
            date_range: Filter by date range
            
        Returns:
            Search results
        """
        try:
            # Build metadata filters
            filters = {}
            
            if file_types:
                filters["file_type"] = {"$in": file_types}
            
            if date_range:
                start_date, end_date = date_range
                filters["vectorized_at"] = {
                    "$gte": start_date.isoformat(),
                    "$lte": end_date.isoformat()
                }
            
            # Perform search
            results = await self.vector_store.search(
                query=query,
                limit=limit,
                where=filters if filters else None,
                include_distances=True
            )
            
            logger.info(f"Search found {len(results)} results for query: {query[:50]}...")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            return []
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        stats = self.stats.copy()
        
        if stats["start_time"]:
            elapsed = datetime.now() - stats["start_time"]
            stats["elapsed_time"] = elapsed.total_seconds()
            stats["processing_rate"] = (
                stats["files_processed"] / elapsed.total_seconds() 
                if elapsed.total_seconds() > 0 else 0
            )
        
        return stats
    
    async def export_processed_data(self) -> Dict[str, Any]:
        """Export all processed data."""
        try:
            # Export vector store data
            vector_data = await self.vector_store.export_data()
            
            # Get collection statistics
            collection_stats = await self.vector_store.get_collection_stats()
            
            # Combine export data
            export_data = {
                "user_id": self.user_id,
                "privacy_level": self.privacy_filter.privacy_level.value,
                "processing_stats": self.get_processing_stats(),
                "collection_stats": collection_stats,
                "vector_data": vector_data,
                "exported_at": datetime.now().isoformat()
            }
            
            logger.info("Exported processed data successfully")
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export processed data: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close the data processor and cleanup resources."""
        try:
            await self.vector_store.close()
            logger.info("Data processor closed successfully")
            
        except Exception as e:
            logger.error(f"Failed to close data processor: {e}")
    
    # Private methods
    
    def _get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get file information."""
        stat = file_path.stat()
        
        return {
            "name": file_path.name,
            "extension": file_path.suffix.lower(),
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "mime_type": mimetypes.guess_type(str(file_path))[0]
        }
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type from extension."""
        extension = file_path.suffix.lower()
        return self.file_type_mappings.get(extension, FileType.UNKNOWN)
    
    async def _extract_content(self, file_path: Path, file_type: str) -> str:
        """Extract content from file based on type."""
        try:
            if file_type == FileType.TEXT:
                return self._extract_text_content(file_path)
            elif file_type == FileType.PDF:
                return self._extract_pdf_content(file_path)
            elif file_type == FileType.DOCX:
                return self._extract_docx_content(file_path)
            elif file_type == FileType.EXCEL:
                return self._extract_excel_content(file_path)
            elif file_type == FileType.CSV:
                return self._extract_csv_content(file_path)
            elif file_type == FileType.JSON:
                return self._extract_json_content(file_path)
            elif file_type == FileType.XML:
                return self._extract_xml_content(file_path)
            elif file_type == FileType.MARKDOWN:
                return self._extract_markdown_content(file_path)
            elif file_type == FileType.HTML:
                return self._extract_html_content(file_path)
            elif file_type == FileType.IMAGE:
                return self._extract_image_content(file_path)
            elif file_type == FileType.EMAIL:
                return self._extract_email_content(file_path)
            else:
                # Try to read as text
                return self._extract_text_content(file_path)
                
        except Exception as e:
            logger.error(f"Failed to extract content from {file_path}: {e}")
            return ""
    
    def _extract_text_content(self, file_path: Path) -> str:
        """Extract content from text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    def _extract_pdf_content(self, file_path: Path) -> str:
        """Extract content from PDF file."""
        if not pdfplumber:
            raise ImportError("pdfplumber is required for PDF processing")
        
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            logger.error(f"Failed to extract PDF content: {e}")
            return ""
    
    def _extract_docx_content(self, file_path: Path) -> str:
        """Extract content from Word document."""
        if not docx:
            raise ImportError("python-docx is required for Word document processing")
        
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            logger.error(f"Failed to extract DOCX content: {e}")
            return ""
    
    def _extract_excel_content(self, file_path: Path) -> str:
        """Extract content from Excel file."""
        if not pd:
            raise ImportError("pandas is required for Excel processing")
        
        try:
            # Read all sheets
            xl_file = pd.ExcelFile(file_path)
            content = []
            
            for sheet_name in xl_file.sheet_names:
                df = pd.read_excel(xl_file, sheet_name=sheet_name)
                content.append(f"Sheet: {sheet_name}")
                content.append(df.to_string())
                content.append("")
            
            return "\n".join(content)
        except Exception as e:
            logger.error(f"Failed to extract Excel content: {e}")
            return ""
    
    def _extract_csv_content(self, file_path: Path) -> str:
        """Extract content from CSV file."""
        if not pd:
            raise ImportError("pandas is required for CSV processing")
        
        try:
            df = pd.read_csv(file_path)
            return df.to_string()
        except Exception as e:
            logger.error(f"Failed to extract CSV content: {e}")
            return ""
    
    def _extract_json_content(self, file_path: Path) -> str:
        """Extract content from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to extract JSON content: {e}")
            return ""
    
    def _extract_xml_content(self, file_path: Path) -> str:
        """Extract content from XML file."""
        return self._extract_text_content(file_path)
    
    def _extract_markdown_content(self, file_path: Path) -> str:
        """Extract content from Markdown file."""
        return self._extract_text_content(file_path)
    
    def _extract_html_content(self, file_path: Path) -> str:
        """Extract content from HTML file."""
        try:
            from bs4 import BeautifulSoup
            
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            # Extract text content
            return soup.get_text()
        except ImportError:
            # Fallback to raw HTML if BeautifulSoup not available
            return self._extract_text_content(file_path)
        except Exception as e:
            logger.error(f"Failed to extract HTML content: {e}")
            return ""
    
    def _extract_image_content(self, file_path: Path) -> str:
        """Extract text from image using OCR."""
        if not Image or not pytesseract:
            logger.warning("PIL and pytesseract are required for image OCR")
            return f"Image file: {file_path.name}"
        
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            logger.error(f"Failed to extract image content: {e}")
            return f"Image file: {file_path.name}"
    
    def _extract_email_content(self, file_path: Path) -> str:
        """Extract content from email file."""
        # This is a simplified implementation
        # In practice, you'd use email parsing libraries
        return self._extract_text_content(file_path)
    
    async def _process_content(
        self,
        content: str,
        file_info: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process extracted content."""
        try:
            # Apply privacy filtering
            safe_content, detected_pii = self.privacy_filter.anonymize_text(content)
            
            # Analyze content
            analysis = await self.analyze_content(safe_content, file_info.get("extension", ""))
            
            # Create document schema
            schema = await self.create_document_schema(safe_content, file_info)
            
            # Prepare metadata for vectorization
            vector_metadata = {
                "file_name": file_info["name"],
                "file_type": file_info["extension"],
                "file_size": file_info["size"],
                "processed_at": datetime.now().isoformat(),
                "privacy_filtered": len(detected_pii) > 0,
                "pii_count": len(detected_pii)
            }
            
            if metadata:
                vector_metadata.update(metadata)
            
            # Vectorize content
            doc_ids = await self.vectorize_document(safe_content, vector_metadata)
            
            return {
                "original_content": content,
                "safe_content": safe_content,
                "detected_pii": detected_pii,
                "analysis": analysis,
                "schema": schema,
                "vector_ids": doc_ids,
                "processed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process content: {e}")
            return {"error": str(e)}
    
    def _update_stats(self, file_info: Dict[str, Any], file_type: str):
        """Update processing statistics."""
        self.stats["files_processed"] += 1
        self.stats["total_size"] += file_info["size"]
        
        if file_type not in self.stats["by_type"]:
            self.stats["by_type"][file_type] = 0
        self.stats["by_type"][file_type] += 1
    
    def _get_files_in_directory(
        self,
        directory_path: Path,
        recursive: bool,
        file_patterns: Optional[List[str]],
        max_files: Optional[int]
    ) -> List[Path]:
        """Get list of files in directory."""
        files = []
        
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        for file_path in directory_path.glob(pattern):
            if file_path.is_file():
                # Check file patterns
                if file_patterns:
                    match = False
                    for pattern in file_patterns:
                        if file_path.match(pattern):
                            match = True
                            break
                    if not match:
                        continue
                
                files.append(file_path)
                
                # Check max files limit
                if max_files and len(files) >= max_files:
                    break
        
        return files
    
    def _extract_key_phrases(self, content: str) -> List[str]:
        """Extract key phrases from content."""
        # Simple implementation - in practice, use NLP libraries
        words = content.lower().split()
        word_freq = {}
        
        for word in words:
            if len(word) > 3:  # Skip short words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top 10 most frequent words
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10]]
    
    def _extract_entities(self, content: str) -> List[Dict[str, str]]:
        """Extract entities from content."""
        # Simple implementation - in practice, use NER models
        entities = []
        
        # Look for email addresses
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        for email in emails:
            entities.append({"type": "email", "value": email})
        
        return entities
    
    def _classify_content(self, content: str) -> Dict[str, Any]:
        """Classify content type and topic."""
        # Simple implementation - in practice, use ML models
        content_lower = content.lower()
        
        # Detect content type
        if "email" in content_lower or "@" in content:
            content_type = "email"
        elif "report" in content_lower or "analysis" in content_lower:
            content_type = "report"
        elif "meeting" in content_lower or "agenda" in content_lower:
            content_type = "meeting"
        else:
            content_type = "general"
        
        # Detect topic
        topics = []
        if "finance" in content_lower or "budget" in content_lower:
            topics.append("finance")
        if "project" in content_lower or "task" in content_lower:
            topics.append("project")
        if "meeting" in content_lower or "discussion" in content_lower:
            topics.append("meeting")
        
        return {
            "content_type": content_type,
            "topics": topics,
            "confidence": 0.7  # Placeholder confidence
        }
    
    def _generate_summary(self, content: str) -> str:
        """Generate a summary of the content."""
        # Simple implementation - in practice, use summarization models
        sentences = content.split('. ')
        
        if len(sentences) <= 3:
            return content
        
        # Take first 2 sentences as summary
        summary = '. '.join(sentences[:2])
        if not summary.endswith('.'):
            summary += '.'
        
        return summary
    
    def _analyze_document_structure(self, content: str) -> Dict[str, Any]:
        """Analyze document structure."""
        lines = content.split('\n')
        
        # Count different types of content
        headers = [line for line in lines if line.strip() and (line.startswith('#') or line.isupper())]
        paragraphs = [line for line in lines if line.strip() and len(line) > 50]
        
        # Detect language (simplified)
        language = "en"  # Default to English
        
        structure = {
            "type": "document",
            "language": language,
            "line_count": len(lines),
            "header_count": len(headers),
            "paragraph_count": len(paragraphs),
            "sections": headers[:5],  # Top 5 headers
            "tags": []
        }
        
        return structure
    
    def _generate_document_id(self, content: str, file_info: Dict[str, Any]) -> str:
        """Generate unique document ID."""
        # Create hash based on content and file info
        hash_input = f"{content[:1000]}{file_info['name']}{file_info['size']}"
        doc_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
        
        return f"{self.user_id}_{doc_hash}_{int(datetime.now().timestamp())}"
    
    def _split_text_into_chunks(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int
    ) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending within the last 100 characters
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + chunk_size - 100:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - chunk_overlap
        
        return chunks 