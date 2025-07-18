"""
Vector Store for Project Zohar.

This module provides vector storage and semantic search capabilities
using ChromaDB and sentence transformers.
"""

import asyncio
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
import logging

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from config.settings import get_settings
from ..agent.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    """
    Vector storage and semantic search using ChromaDB.
    
    This class provides:
    - Document embedding and storage
    - Semantic search and retrieval
    - Batch processing capabilities
    - Collection management
    """
    
    def __init__(
        self,
        user_id: str,
        collection_name: Optional[str] = None,
        embedding_model: Optional[str] = None,
        persist_directory: Optional[Path] = None
    ):
        """
        Initialize the vector store.
        
        Args:
            user_id: Unique identifier for the user
            collection_name: Name of the collection (defaults to user_id)
            embedding_model: Name of the embedding model to use
            persist_directory: Directory to persist the database
        """
        if chromadb is None:
            raise ImportError("ChromaDB is required but not installed. Run: pip install chromadb")
        
        self.user_id = user_id
        self.settings = get_settings()
        
        # Collection setup
        self.collection_name = collection_name or f"user_{user_id}"
        
        # Embedding model setup
        self.embedding_model_name = embedding_model or self.settings.embedding_model
        self.embedding_function = None
        self.local_model = None
        
        # Database setup
        if persist_directory:
            self.persist_directory = persist_directory
        else:
            self.persist_directory = self.settings.data_dir / "vectordb" / user_id
        
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # ChromaDB client and collection
        self.client = None
        self.collection = None
        
        # State
        self.is_initialized = False
        
        logger.info(f"Vector store initialized for user {user_id}")
    
    async def initialize(self) -> bool:
        """
        Initialize the vector store.
        
        Returns:
            Success status
        """
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Initialize embedding function
            await self._initialize_embedding_function()
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
                logger.info(f"Loaded existing collection: {self.collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"user_id": self.user_id, "created_at": datetime.now().isoformat()}
                )
                logger.info(f"Created new collection: {self.collection_name}")
            
            self.is_initialized = True
            logger.info(f"Vector store initialized successfully for user {self.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            return False
    
    async def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of document texts
            metadatas: Optional list of metadata dictionaries
            ids: Optional list of document IDs
            
        Returns:
            List of document IDs
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Generate IDs if not provided
            if ids is None:
                ids = [self._generate_doc_id(doc) for doc in documents]
            
            # Prepare metadata
            if metadatas is None:
                metadatas = [{"added_at": datetime.now().isoformat()} for _ in documents]
            else:
                # Ensure all metadata dicts have added_at
                for metadata in metadatas:
                    if "added_at" not in metadata:
                        metadata["added_at"] = datetime.now().isoformat()
            
            # Add to collection
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to vector store")
            return ids
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        where: Optional[Dict[str, Any]] = None,
        include_distances: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            where: Optional metadata filter
            include_distances: Whether to include similarity distances
            
        Returns:
            List of search results
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Perform search
            include_list = ["documents", "metadatas"]
            if include_distances:
                include_list.append("distances")
            
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=where,
                include=include_list
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results["documents"][0])):
                result = {
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i]
                }
                
                if include_distances:
                    result["distance"] = results["distances"][0][i]
                    result["similarity"] = 1 - results["distances"][0][i]  # Convert distance to similarity
                
                formatted_results.append(result)
            
            logger.debug(f"Found {len(formatted_results)} results for query: {query[:50]}...")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            return []
    
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
            
            if results["documents"]:
                return {
                    "id": results["ids"][0],
                    "content": results["documents"][0],
                    "metadata": results["metadatas"][0]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None
    
    async def update_document(
        self,
        doc_id: str,
        document: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update a document.
        
        Args:
            doc_id: Document ID
            document: New document content (optional)
            metadata: New metadata (optional)
            
        Returns:
            Success status
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            update_data = {"ids": [doc_id]}
            
            if document is not None:
                update_data["documents"] = [document]
            
            if metadata is not None:
                metadata["updated_at"] = datetime.now().isoformat()
                update_data["metadatas"] = [metadata]
            
            self.collection.update(**update_data)
            
            logger.info(f"Updated document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False
    
    async def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Success status
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
    
    async def delete_documents(self, where: Dict[str, Any]) -> int:
        """
        Delete documents matching criteria.
        
        Args:
            where: Metadata filter criteria
            
        Returns:
            Number of documents deleted
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # First get the documents to count them
            results = self.collection.get(where=where, include=["metadatas"])
            count = len(results["ids"])
            
            if count > 0:
                # Delete the documents
                self.collection.delete(where=where)
                logger.info(f"Deleted {count} documents")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return 0
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Get collection info
            count = self.collection.count()
            
            # Get sample of documents for analysis
            sample_results = self.collection.peek(limit=min(100, count))
            
            # Calculate average content length
            avg_length = 0
            if sample_results["documents"]:
                total_length = sum(len(doc) for doc in sample_results["documents"])
                avg_length = total_length / len(sample_results["documents"])
            
            # Get unique metadata keys
            metadata_keys = set()
            if sample_results["metadatas"]:
                for metadata in sample_results["metadatas"]:
                    metadata_keys.update(metadata.keys())
            
            return {
                "collection_name": self.collection_name,
                "total_documents": count,
                "average_content_length": round(avg_length, 2),
                "metadata_keys": list(metadata_keys),
                "embedding_model": self.embedding_model_name,
                "persist_directory": str(self.persist_directory),
                "is_initialized": self.is_initialized
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}
    
    async def semantic_search_with_filters(
        self,
        query: str,
        filters: Dict[str, Any],
        limit: int = 10,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search with metadata filters and similarity threshold.
        
        Args:
            query: Search query
            filters: Metadata filters
            limit: Maximum results
            min_similarity: Minimum similarity threshold
            
        Returns:
            Filtered search results
        """
        try:
            results = await self.search(
                query=query,
                limit=limit * 2,  # Get more results to filter
                where=filters,
                include_distances=True
            )
            
            # Filter by similarity threshold
            filtered_results = [
                result for result in results
                if result.get("similarity", 0) >= min_similarity
            ]
            
            # Return only the requested number
            return filtered_results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to perform semantic search with filters: {e}")
            return []
    
    async def get_similar_documents(
        self,
        doc_id: str,
        limit: int = 5,
        exclude_self: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find documents similar to a given document.
        
        Args:
            doc_id: Document ID to find similar documents for
            limit: Maximum number of results
            exclude_self: Whether to exclude the source document
            
        Returns:
            List of similar documents
        """
        try:
            # Get the source document
            source_doc = await self.get_document(doc_id)
            if not source_doc:
                return []
            
            # Search for similar documents
            results = await self.search(
                query=source_doc["content"],
                limit=limit + (1 if exclude_self else 0),
                include_distances=True
            )
            
            # Exclude the source document if requested
            if exclude_self:
                results = [r for r in results if r["id"] != doc_id]
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to find similar documents: {e}")
            return []
    
    async def batch_add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        batch_size: int = 100
    ) -> List[str]:
        """
        Add documents in batches for better performance.
        
        Args:
            documents: List of documents
            metadatas: Optional metadata list
            batch_size: Size of each batch
            
        Returns:
            List of all document IDs
        """
        try:
            all_ids = []
            
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size] if metadatas else None
                
                batch_ids = await self.add_documents(
                    documents=batch_docs,
                    metadatas=batch_metadatas
                )
                
                all_ids.extend(batch_ids)
                
                logger.info(f"Processed batch {i // batch_size + 1}, added {len(batch_ids)} documents")
            
            return all_ids
            
        except Exception as e:
            logger.error(f"Failed to batch add documents: {e}")
            raise
    
    async def export_data(self) -> Dict[str, Any]:
        """
        Export all data for backup.
        
        Returns:
            Dictionary containing all documents and metadata
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Get all documents
            all_results = self.collection.get(include=["documents", "metadatas"])
            
            export_data = {
                "collection_name": self.collection_name,
                "user_id": self.user_id,
                "embedding_model": self.embedding_model_name,
                "export_timestamp": datetime.now().isoformat(),
                "documents": []
            }
            
            # Format documents
            for i, doc_id in enumerate(all_results["ids"]):
                export_data["documents"].append({
                    "id": doc_id,
                    "content": all_results["documents"][i],
                    "metadata": all_results["metadatas"][i]
                })
            
            logger.info(f"Exported {len(export_data['documents'])} documents")
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return {}
    
    async def close(self):
        """Close the vector store and cleanup resources."""
        try:
            self.is_initialized = False
            self.collection = None
            self.client = None
            
            # Cleanup local model if loaded
            if self.local_model:
                del self.local_model
                self.local_model = None
            
            logger.info(f"Vector store closed for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to close vector store: {e}")
    
    # Private methods
    
    async def _initialize_embedding_function(self):
        """Initialize the embedding function."""
        try:
            # Try to use local embedding model first
            if SentenceTransformer and self.embedding_model_name:
                try:
                    self.local_model = SentenceTransformer(self.embedding_model_name)
                    self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name=self.embedding_model_name
                    )
                    logger.info(f"Using local embedding model: {self.embedding_model_name}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load local embedding model: {e}")
            
            # Fallback to default embedding function
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
            logger.info("Using default embedding function")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding function: {e}")
            raise
    
    def _generate_doc_id(self, content: str) -> str:
        """Generate a unique document ID based on content hash."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.user_id}_{timestamp}_{content_hash[:8]}"
