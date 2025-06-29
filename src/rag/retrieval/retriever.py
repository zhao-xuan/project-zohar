"""
Data Retrieval classes for RAG (Retrieval-Augmented Generation)
"""
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
import re
import datetime
from collections import defaultdict
import json

# Placeholder imports - these would need actual implementations
# from chromadb import Client
# from sentence_transformers import SentenceTransformer


class BaseRetriever(ABC):
    """Base class for data retrieval"""
    
    @abstractmethod
    async def retrieve_relevant_data(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant data for a query"""
        pass


class PersonalDataRetriever(BaseRetriever):
    """
    Retriever for personal data with full access to private information
    Enhanced with metadata-based search capabilities
    """
    
    def __init__(self):
        # Initialize vector database connection
        self.db_path = Path("data/camel_vector_db")
        self.chroma_client = None
        self.collections = {}
        self.embedding_function = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize connection to ChromaDB"""
        try:
            if self.db_path.exists():
                # Connect to existing database
                self.chroma_client = chromadb.PersistentClient(path=str(self.db_path))
                
                # Set up embedding function (same as used in processing)
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
                
                # Get available collections
                self._load_collections()
                print(f"✅ Connected to vector database with {len(self.collections)} collections")
            else:
                print("⚠️ Vector database not found. Please run the file processing first.")
        except Exception as e:
            print(f"❌ Failed to connect to vector database: {e}")
    
    def _load_collections(self):
        """Load all available collections"""
        try:
            collections_info = self.chroma_client.list_collections()
            for collection_info in collections_info:
                collection = self.chroma_client.get_collection(
                    name=collection_info.name,
                    embedding_function=self.embedding_function
                )
                self.collections[collection_info.name] = collection
                print(f"  📁 Loaded collection: {collection_info.name} ({collection.count()} documents)")
        except Exception as e:
            print(f"❌ Failed to load collections: {e}")
    
    def _parse_date_from_text(self, text: str) -> Optional[datetime.datetime]:
        """Extract date/time from chat message text"""
        # WhatsApp format: [3/13/22, 10:11:07 PM]
        whatsapp_pattern = r'\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}:\d{2}\s*[AP]M)\]'
        match = re.search(whatsapp_pattern, text, re.IGNORECASE)
        
        if match:
            date_str = match.group(1)
            time_str = match.group(2)
            
            try:
                # Parse date
                date_parts = date_str.split('/')
                month, day, year = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
                if year < 100:  # Handle 2-digit years
                    year += 2000
                
                # Parse time
                time_obj = datetime.datetime.strptime(time_str, '%I:%M:%S %p').time()
                
                # Combine date and time
                return datetime.datetime.combine(datetime.date(year, month, day), time_obj)
            except (ValueError, IndexError):
                pass
        
        # Alternative formats can be added here
        # ISO format: 2022-03-13T22:11:07
        iso_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'
        match = re.search(iso_pattern, text)
        if match:
            try:
                return datetime.datetime.fromisoformat(match.group(1))
            except ValueError:
                pass
        
        return None
    
    def _extract_sender_from_message(self, text: str) -> Optional[str]:
        """Extract sender name from chat message"""
        # WhatsApp format: [date] Sender Name: message content
        sender_pattern = r'\]\s*([^:]+):\s'
        match = re.search(sender_pattern, text)
        
        if match:
            sender = match.group(1).strip()
            # Filter out system messages
            if sender and not sender.startswith('‎'):
                return sender
        
        return None
    
    def _detect_query_type(self, query: str) -> Dict[str, Any]:
        """Detect the type of query and extract metadata criteria"""
        query_lower = query.lower()
        criteria = {
            "type": "general",
            "temporal": None,
            "sender": None,
            "date_range": None,
            "file_type": None,
            "metadata_filters": {}
        }
        
        # Detect temporal queries
        temporal_keywords = {
            "earliest": "earliest",
            "first": "earliest", 
            "oldest": "earliest",
            "latest": "latest",
            "last": "latest",
            "newest": "latest",
            "recent": "latest"
        }
        
        for keyword, temporal_type in temporal_keywords.items():
            if keyword in query_lower:
                criteria["temporal"] = temporal_type
                criteria["type"] = "temporal"
                break
        
        # Detect sender queries
        sender_patterns = [
            r"from\s+(\w+)",
            r"by\s+(\w+)",
            r"sent\s+by\s+(\w+)",
            r"(\w+)\s+sent",
            r"messages?\s+from\s+(\w+)"
        ]
        
        for pattern in sender_patterns:
            match = re.search(pattern, query_lower)
            if match:
                criteria["sender"] = match.group(1).title()
                criteria["type"] = "sender_based"
                break
        
        # Detect date-based queries
        date_patterns = [
            r"on\s+(\d{1,2}/\d{1,2}/\d{2,4})",
            r"(\d{4}-\d{2}-\d{2})",
            r"in\s+(\w+)\s+(\d{4})",  # "in March 2022"
            r"(\w+)\s+(\d{1,2}),?\s+(\d{4})"  # "March 13, 2022"
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, query_lower)
            if match:
                criteria["type"] = "date_based"
                # More sophisticated date parsing can be added here
                break
        
        # Detect file type queries
        file_type_keywords = {
            "document": [".pdf", ".doc", ".docx"],
            "image": [".jpg", ".jpeg", ".png", ".gif"],
            "audio": [".mp3", ".opus", ".wav"],
            "video": [".mp4", ".mov", ".avi"]
        }
        
        for file_type, extensions in file_type_keywords.items():
            if file_type in query_lower:
                criteria["file_type"] = extensions
                criteria["type"] = "file_based"
                break
        
        return criteria
    
    def _filter_by_metadata(self, results: List[Dict[str, Any]], criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter results based on metadata criteria"""
        filtered_results = []
        
        for result in results:
            content = result.get('original_content', result.get('content', ''))
            metadata = result.get('metadata', {})
            
            # Apply sender filter
            if criteria.get("sender"):
                sender = self._extract_sender_from_message(content)
                if not sender or criteria["sender"].lower() not in sender.lower():
                    continue
            
            # Apply file type filter
            if criteria.get("file_type"):
                file_ext = metadata.get('file_extension', '').lower()
                if file_ext not in criteria["file_type"]:
                    continue
            
            # Extract date for temporal filtering
            message_date = self._parse_date_from_text(content)
            if message_date:
                result['parsed_date'] = message_date
            
            filtered_results.append(result)
        
        return filtered_results
    
    def _sort_by_temporal_criteria(self, results: List[Dict[str, Any]], temporal_type: str) -> List[Dict[str, Any]]:
        """Sort results based on temporal criteria"""
        # Filter results that have dates
        dated_results = [r for r in results if 'parsed_date' in r]
        undated_results = [r for r in results if 'parsed_date' not in r]
        
        if not dated_results:
            return results
        
        if temporal_type == "earliest":
            dated_results.sort(key=lambda x: x['parsed_date'])
        elif temporal_type == "latest":
            dated_results.sort(key=lambda x: x['parsed_date'], reverse=True)
        
        # Combine dated and undated results
        return dated_results + undated_results
    
    def _enhance_query(self, query: str) -> List[str]:
        """
        Enhance user query with multiple search variations for better retrieval
        """
        # Clean and normalize the query
        base_query = query.lower().strip()
        
        # Generate query variations
        queries = [query]  # Original query
        
        # Extract key terms for document searches
        key_terms = []
        
        # Document-specific terms (generic approach)
        if any(term in base_query for term in ['agreement', 'contract', 'document', 'file', 'certificate', 'receipt', 'invoice']):
            # Extract the main subject/type from the query
            query_words = base_query.split()
            for word in query_words:
                if word not in ['agreement', 'contract', 'document', 'file', 'the', 'a', 'an']:
                    # Add combinations with document types
                    key_terms.extend([
                        f"{word} agreement",
                        f"{word} contract", 
                        f"{word} document",
                        f"{word} file"
                    ])
        
        # Chat/message specific terms
        if any(term in base_query for term in ['message', 'text', 'chat', 'said', 'wrote']):
            # Remove temporal and sender keywords for content search
            content_words = []
            skip_words = {'earliest', 'first', 'latest', 'last', 'from', 'by', 'sent', 'on', 'in'}
            for word in base_query.split():
                if word not in skip_words and not re.match(r'\d+/\d+/\d+', word):
                    content_words.append(word)
            if content_words:
                key_terms.append(' '.join(content_words))
        
        # Remove common stopwords from query
        stopwords = {'find', 'the', 'show', 'me', 'where', 'is', 'can', 'you', 'i', 'need', 'want'}
        words = base_query.split()
        filtered_words = [word for word in words if word not in stopwords]
        if len(filtered_words) > 0:
            key_terms.append(' '.join(filtered_words))
        
        # Add key terms to queries
        queries.extend(key_terms)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)
        
        return unique_queries[:3]  # Limit to top 3 variations
    
    def _enhance_content_description(self, content: str, metadata: Dict[str, Any], preserve_terms: List[str] = None) -> str:
        """
        Enhance content description to make it clearer for LLM what the document contains
        
        Args:
            content: The original content
            metadata: Content metadata
            preserve_terms: Important terms from search query to preserve in description
        """
        filename = metadata.get('filename', '')
        file_ext = metadata.get('file_extension', '')
        
        # Extract important terms that should be preserved
        preserved_context = ""
        if preserve_terms:
            import re  # Import at the top of the logic block
            for term in preserve_terms:
                if term.lower() in content.lower():
                    # Find context around the term
                    pattern = rf'.{{0,50}}{re.escape(term)}.{{0,50}}'
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        preserved_context = f"\n🔍 Key mention: \"{matches[0].strip()}\""
                        break
        
        # Extract date and sender for chat messages
        message_date = self._parse_date_from_text(content)
        sender = self._extract_sender_from_message(content)
        
        # Check if this is a chat message
        if message_date and sender:
            date_str = message_date.strftime('%Y-%m-%d %H:%M:%S')
            # Extract the actual message content (remove metadata formatting)
            content_lines = content.split('\n')
            actual_message = ""
            
            # If we have preserve terms, look for them in the full content first
            if preserve_terms:
                for term in preserve_terms:
                    if term.lower() in content.lower():
                        # Find a larger portion of content that includes the search term
                        import re
                        # Get up to 300 chars around the term
                        pattern = rf'.{{0,150}}{re.escape(term)}.{{0,150}}'
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            actual_message = matches[0].strip()
                            break
            
            # If we didn't find preserved terms, use the normal extraction
            if not actual_message:
                for line in content_lines:
                    if not line.startswith('[') and ':' in line and not line.startswith('👤') and not line.startswith('📅'):
                        # This might be the actual message content
                        actual_message = line.split(':', 1)[-1].strip() if ':' in line else line.strip()
                        break
                
                if not actual_message:
                    actual_message = content[:200] + "..." if len(content) > 200 else content
            
            return f"💬 CHAT MESSAGE:\n" + \
                   f"📅 Date: {date_str}\n" + \
                   f"👤 Sender: {sender}\n" + \
                   f"📝 Message: {actual_message}" + \
                   preserved_context
        
        # Check if this is a document file reference
        elif content.startswith('Document file:') and 'WhatsApp attachment' in content:
            # Extract the actual filename from the content
            match = re.search(r'Document file: (.+?) \(WhatsApp attachment\)', content)
            if match:
                actual_filename = match.group(1)
                
                # Analyze filename for content type (generic approach)
                filename_lower = actual_filename.lower()
                
                # Detect document types by keywords
                if any(term in filename_lower for term in ['agreement', 'contract']):
                    doc_type = "AGREEMENT/CONTRACT"
                    description = "This is a legal agreement or contract document"
                elif any(term in filename_lower for term in ['receipt', 'invoice', 'bill']):
                    doc_type = "RECEIPT/INVOICE"
                    description = "This is a financial document"
                elif any(term in filename_lower for term in ['certificate', 'certification', 'diploma']):
                    doc_type = "CERTIFICATE"
                    description = "This is an official certificate or certification document"
                elif any(term in filename_lower for term in ['report', 'summary', 'analysis']):
                    doc_type = "REPORT"
                    description = "This is a report or analysis document"
                elif file_ext in ['.pdf', '.doc', '.docx']:
                    doc_type = "DOCUMENT FILE"
                    description = "This is a document file"
                elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    doc_type = "IMAGE FILE"
                    description = "This is an image file"
                elif file_ext in ['.mp3', '.opus', '.wav', '.m4a']:
                    doc_type = "AUDIO FILE"
                    description = "This is an audio file"
                elif file_ext in ['.mp4', '.mov', '.avi']:
                    doc_type = "VIDEO FILE"
                    description = "This is a video file"
                else:
                    doc_type = "FILE"
                    description = "This is a file"
                
                return f"📄 {doc_type}: {actual_filename}\n" + \
                       f"{description} shared via WhatsApp.\n" + \
                       f"File type: {file_ext}\n" + \
                       f"Status: Available for review" + \
                       preserved_context
        
        # Check if this is actual document content (not just file reference)
        # Detect various document types by content patterns
        elif any(term in content.upper() for term in ['AGREEMENT', 'CONTRACT', 'TERMS', 'CONDITIONS']):
            doc_type = "AGREEMENT/CONTRACT"
            if 'LODGER' in content.upper() or 'RENTAL' in content.upper():
                doc_type = "RENTAL/LODGER AGREEMENT"
            elif 'EMPLOYMENT' in content.upper() or 'WORK' in content.upper():
                doc_type = "EMPLOYMENT AGREEMENT"
            elif 'SERVICE' in content.upper():
                doc_type = "SERVICE AGREEMENT"
            
            return f"📄 {doc_type} CONTENT:\n" + \
                   f"This is the actual content of a {doc_type.lower()} document.\n" + \
                   f"File: {filename}\n" + \
                   f"Content preview:\n{content[:300]}..." + \
                   preserved_context
        
        # Check for other document content types
        elif any(term in content.upper() for term in ['CERTIFICATE', 'CERTIFICATION', 'DIPLOMA']):
            return f"📄 CERTIFICATE CONTENT:\n" + \
                   f"This is the actual content of a certificate or certification document.\n" + \
                   f"File: {filename}\n" + \
                   f"Content preview:\n{content[:300]}..." + \
                   preserved_context
        
        elif any(term in content.upper() for term in ['RECEIPT', 'INVOICE', 'BILL', 'PAYMENT']):
            return f"📄 FINANCIAL DOCUMENT CONTENT:\n" + \
                   f"This is the actual content of a financial document (receipt/invoice/bill).\n" + \
                   f"File: {filename}\n" + \
                   f"Content preview:\n{content[:300]}..." + \
                   preserved_context
        
        # Default enhancement for other content
        else:
            return content + preserved_context
    
    async def retrieve_relevant_data(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant personal data for a query with enhanced search and formatting
        
        Args:
            query: The search query
            limit: Maximum number of results to return (default: 5)
            
        Returns:
            List of relevant data items with enhanced metadata and descriptions
        """
        if not self.chroma_client or not self.collections:
            # Fallback to placeholder if database not available
            return self._get_placeholder_data(query)
        
        # Detect query type and extract criteria
        criteria = self._detect_query_type(query)
        
        # Extract key search terms from query for preservation
        search_terms = []
        query_words = query.lower().split()
        # Filter out common words and focus on important terms (including short keywords like "TV")
        stop_words = {'top', 'list', 'find', 'search', 'messages', 'that', 'mention', 'the', 'and', 'or', 'in', 'on', 'at', 'for', 'with', 'by', 'contain', 'keyword'}
        search_terms = [word for word in query_words if word not in stop_words and len(word) >= 2]  # Changed from > 2 to >= 2
        
        try:
            all_results = []
            
            # For simple searches (like "Jonathan"), use direct query without enhancement
            if len(query.split()) <= 2 and not any(word in query.lower() for word in ['earliest', 'latest', 'from', 'by', 'on', 'in']):
                # Simple, direct search
                query_variations = [query]
            else:
                # Complex query - use enhancement
                query_variations = self._enhance_query(query)
            
            # Search across all collections
            for collection_name, collection in self.collections.items():
                try:
                    for search_query in query_variations:
                        # Adjust search parameters based on query type
                        search_limit = limit * 3 if criteria["type"] in ["temporal", "sender_based"] else limit * 2
                        search_limit = max(search_limit, 10)  # Minimum 10 results for better filtering
                        
                        # Query the collection
                        query_results = collection.query(
                            query_texts=[search_query],
                            n_results=min(search_limit, 50),
                            include=['documents', 'metadatas', 'distances']
                        )
                        
                        # Process results
                        if query_results['documents'] and query_results['documents'][0]:
                            for i, doc in enumerate(query_results['documents'][0]):
                                metadata = query_results['metadatas'][0][i] if query_results['metadatas'] else {}
                                distance = query_results['distances'][0][i] if query_results['distances'] else 1.0
                                
                                # Convert distance to similarity score (ChromaDB uses cosine distance)
                                # For cosine distance: similarity = 1 - distance/2 (normalized to 0-1 range)
                                similarity = max(0, 1 - (distance / 2))
                                
                                # Create unique ID for deduplication
                                doc_id = f"{metadata.get('filename', '')}_{metadata.get('chunk_id', 0)}"
                                
                                # Enhanced content description with search term preservation
                                enhanced_content = self._enhance_content_description(doc, metadata, search_terms)
                                
                                result_item = {
                                    "source": collection_name,
                                    "content": enhanced_content,
                                    "original_content": doc,  # Keep original for reference
                                    "metadata": {
                                        **metadata,
                                        "collection": collection_name,
                                        "original_metadata": metadata,
                                        "search_query": search_query,
                                        "doc_id": doc_id
                                    },
                                    "relevance_score": similarity
                                }
                                all_results.append(result_item)
                
                except Exception as e:
                    print(f"Error querying collection {collection_name}: {e}")
                    continue
            
            # Deduplicate results based on doc_id
            seen_ids = set()
            unique_results = []
            for result in all_results:
                doc_id = result['metadata'].get('doc_id')
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    unique_results.append(result)
            
            # Apply metadata filtering
            filtered_results = self._filter_by_metadata(unique_results, criteria)
            
            # Apply temporal sorting if needed
            if criteria["temporal"]:
                filtered_results = self._sort_by_temporal_criteria(filtered_results, criteria["temporal"])
            
            # Sort by relevance score for non-temporal queries
            elif criteria["type"] != "temporal":
                filtered_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # Boost document-type results for document queries
            if any(term in query.lower() for term in ['agreement', 'contract', 'document', 'file']):
                document_results = []
                other_results = []
                
                for result in filtered_results:
                    if ('agreement' in result['content'].lower() or 
                        'contract' in result['content'].lower() or
                        result['metadata'].get('file_extension') in ['.pdf', '.doc', '.docx']):
                        document_results.append(result)
                    else:
                        other_results.append(result)
                
                # Prioritize document results
                final_results = document_results + other_results
            else:
                final_results = filtered_results
            
            return final_results[:limit]
            
        except Exception as e:
            print(f"❌ Error retrieving data: {e}")
            return self._get_placeholder_data(query)
    
    async def search_by_sender(self, sender_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for messages from a specific sender"""
        query = f"messages from {sender_name}"
        return await self.retrieve_relevant_data(query, limit)
    
    async def search_by_date_range(self, start_date: str, end_date: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for messages within a date range"""
        if end_date:
            query = f"messages between {start_date} and {end_date}"
        else:
            query = f"messages on {start_date}"
        return await self.retrieve_relevant_data(query, limit)
    
    async def get_earliest_messages(self, sender: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the earliest messages, optionally from a specific sender"""
        if sender:
            query = f"earliest messages from {sender}"
        else:
            query = "earliest messages"
        return await self.retrieve_relevant_data(query, limit)
    
    async def get_latest_messages(self, sender: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the latest messages, optionally from a specific sender"""
        if sender:
            query = f"latest messages from {sender}"
        else:
            query = "latest messages"
        return await self.retrieve_relevant_data(query, limit)
    
    async def get_messages_by_date(self, target_date: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all messages from a specific date"""
        query = f"messages on {target_date}"
        return await self.retrieve_relevant_data(query, limit)
    
    async def analyze_conversation_timeline(self, sender: str = None) -> Dict[str, Any]:
        """Analyze the timeline of conversations"""
        # Get a large sample of messages
        if sender:
            results = await self.search_by_sender(sender, limit=100)
        else:
            results = await self.retrieve_relevant_data("messages", limit=100)
        
        # Extract dates and analyze
        dates = []
        daily_counts = defaultdict(int)
        
        for result in results:
            content = result.get('original_content', '')
            message_date = self._parse_date_from_text(content)
            
            if message_date:
                dates.append(message_date)
                date_key = message_date.strftime('%Y-%m-%d')
                daily_counts[date_key] += 1
        
        if not dates:
            return {"error": "No dated messages found"}
        
        dates.sort()
        
        return {
            "total_messages": len(dates),
            "date_range": {
                "earliest": dates[0].strftime('%Y-%m-%d %H:%M:%S'),
                "latest": dates[-1].strftime('%Y-%m-%d %H:%M:%S')
            },
            "daily_counts": dict(daily_counts),
            "most_active_days": sorted(daily_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def _get_placeholder_data(self, query: str) -> List[Dict[str, Any]]:
        """Return placeholder data when database is not available"""
        return [
            {
                "source": "vector_database_unavailable",
                "content": f"I don't have access to your processed data right now. Please ensure the vector database has been created by running the file processing. You asked about: {query}",
                "metadata": {
                    "type": "error",
                    "status": "database_unavailable"
                },
                "relevance_score": 0.1
            }
        ]
    
    async def search_emails(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search specifically in email data"""
        # Get all results and filter for email content
        all_results = await self.retrieve_relevant_data(query, limit * 2)
        email_results = []
        
        for result in all_results:
            metadata = result.get('metadata', {})
            content = result.get('content', '').lower()
            
            # Check if this is email-related content
            if (metadata.get('file_extension') in ['.eml', '.msg'] or
                'email' in metadata.get('content_type', '') or
                any(keyword in content for keyword in ['@', 'subject:', 'from:', 'to:'])):
                email_results.append(result)
                
            if len(email_results) >= limit:
                break
        
        return email_results
    
    async def search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search specifically in document data"""
        # Get all results and filter for document content
        all_results = await self.retrieve_relevant_data(query, limit * 2)
        doc_results = []
        
        for result in all_results:
            metadata = result.get('metadata', {})
            
            # Check if this is document content
            if metadata.get('file_extension') in ['.pdf', '.docx', '.txt', '.md', '.doc']:
                doc_results.append(result)
                
            if len(doc_results) >= limit:
                break
        
        return doc_results
    
    async def search_chat_history(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search in chat history for tone and context"""
        # Get all results and filter for chat content
        all_results = await self.retrieve_relevant_data(query, limit * 2)
        chat_results = []
        
        for result in all_results:
            metadata = result.get('metadata', {})
            content = result.get('content', '').lower()
            source = result.get('source', '').lower()
            
            # Check if this is chat/conversation content
            if (metadata.get('file_extension') in ['.txt', '.html'] or
                'chat' in source or 'whatsapp' in source or 'wechat' in source or
                any(keyword in content for keyword in [':', '[', 'am]', 'pm]']) or
                'conversation' in metadata.get('content_type', '')):
                chat_results.append(result)
                
            if len(chat_results) >= limit:
                break
        
        return chat_results
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the connected database"""
        if not self.chroma_client:
            return {"status": "disconnected", "collections": []}
        
        info = {
            "status": "connected",
            "database_path": str(self.db_path),
            "collections": []
        }
        
        for name, collection in self.collections.items():
            try:
                count = collection.count()
                info["collections"].append({
                    "name": name,
                    "document_count": count
                })
            except:
                info["collections"].append({
                    "name": name,
                    "document_count": "unknown"
                })
        
        return info


class PublicDataRetriever(BaseRetriever):
    """
    Retriever for public data only - restricted access
    """
    
    def __init__(self):
        # Initialize connection to public data only
        self.personal_retriever = PersonalDataRetriever()
    
    async def retrieve_relevant_data(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve relevant public data for a query
        
        Args:
            query: The search query
            limit: Maximum number of results (limited for public use)
            
        Returns:
            List of relevant public data items
        """
        # Get data from personal retriever but filter for public information
        all_results = await self.personal_retriever.retrieve_relevant_data(query, limit * 3)
        
        public_results = []
        for result in all_results:
            if self._is_public_information(result):
                # Remove sensitive metadata
                result['metadata'] = self._sanitize_metadata(result.get('metadata', {}))
                public_results.append(result)
                
            if len(public_results) >= limit:
                break
        
        return public_results
    
    async def retrieve_public_data(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve only public-facing information"""
        return await self.retrieve_relevant_data(query, limit=3)
    
    def _is_public_information(self, data_item: Dict[str, Any]) -> bool:
        """Check if a data item is appropriate for public access"""
        metadata = data_item.get("metadata", {})
        content = data_item.get("content", "").lower()
        
        # Check for private indicators in metadata
        if metadata.get("visibility") == "private":
            return False
        
        # Check for sensitive file types
        file_ext = metadata.get("file_extension", "").lower()
        if file_ext in ['.eml', '.msg']:  # Email files
            return False
        
        # Check for sensitive content keywords
        sensitive_keywords = [
            "password", "private", "confidential", "internal", "personal",
            "@", "email", "phone", "address", "ssn", "account", "payment"
        ]
        if any(keyword in content for keyword in sensitive_keywords):
            return False
        
        return True
    
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from metadata"""
        safe_metadata = {}
        
        # Only include safe metadata fields
        safe_fields = ["content_type", "file_extension", "collection"]
        for field in safe_fields:
            if field in metadata:
                safe_metadata[field] = metadata[field]
        
        safe_metadata["visibility"] = "public"
        return safe_metadata 