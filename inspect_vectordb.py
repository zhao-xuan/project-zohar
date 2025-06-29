#!/usr/bin/env python3
"""
Vector Database Inspector for camel_vector_db
Inspects ChromaDB collections, schemas, and content
"""

import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
import json
from collections import defaultdict
from typing import Dict, List, Any
import pandas as pd


class VectorDBInspector:
    """Inspector for ChromaDB vector database"""
    
    def __init__(self, db_path: str = "./data/camel_vector_db"):
        self.db_path = Path(db_path)
        self.client = None
        self.collections = {}
        self.embedding_function = None
        self._connect()
    
    def _connect(self):
        """Connect to the ChromaDB database"""
        try:
            if self.db_path.exists():
                self.client = chromadb.PersistentClient(path=str(self.db_path))
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
                print(f"✅ Connected to ChromaDB at: {self.db_path}")
            else:
                print(f"❌ Database not found at: {self.db_path}")
                return
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            return
    
    def list_collections(self):
        """List all collections in the database"""
        if not self.client:
            return []
        
        try:
            collections_info = self.client.list_collections()
            print(f"\n📁 Collections in database ({len(collections_info)} total):")
            print("=" * 60)
            
            for i, collection_info in enumerate(collections_info, 1):
                collection = self.client.get_collection(
                    name=collection_info.name,
                    embedding_function=self.embedding_function
                )
                count = collection.count()
                self.collections[collection_info.name] = collection
                
                print(f"{i}. {collection_info.name}")
                print(f"   Documents: {count:,}")
                print(f"   ID: {collection_info.id}")
                print()
            
            return list(self.collections.keys())
        except Exception as e:
            print(f"❌ Error listing collections: {e}")
            return []
    
    def inspect_collection_schema(self, collection_name: str):
        """Inspect the schema and metadata structure of a collection"""
        if collection_name not in self.collections:
            print(f"❌ Collection '{collection_name}' not found")
            return
        
        collection = self.collections[collection_name]
        
        try:
            # Get a sample of documents to analyze schema
            sample_data = collection.get(limit=100, include=['documents', 'metadatas', 'ids'])
            
            print(f"\n🔍 Schema Analysis for '{collection_name}':")
            print("=" * 60)
            print(f"Total Documents: {collection.count():,}")
            print(f"Sample Size: {len(sample_data['ids'])}")
            
            # Analyze metadata schema
            if sample_data['metadatas']:
                metadata_keys = set()
                metadata_types = defaultdict(set)
                metadata_samples = defaultdict(list)
                
                for metadata in sample_data['metadatas']:
                    if metadata:
                        for key, value in metadata.items():
                            metadata_keys.add(key)
                            metadata_types[key].add(type(value).__name__)
                            if len(metadata_samples[key]) < 3:
                                metadata_samples[key].append(value)
                
                print(f"\n📋 Metadata Schema ({len(metadata_keys)} fields):")
                print("-" * 40)
                for key in sorted(metadata_keys):
                    types = list(metadata_types[key])
                    samples = metadata_samples[key]
                    print(f"• {key}")
                    print(f"  Type(s): {', '.join(types)}")
                    print(f"  Samples: {samples}")
                    print()
            
            # Analyze document content
            if sample_data['documents']:
                doc_lengths = [len(doc) for doc in sample_data['documents'] if doc]
                
                print(f"\n📄 Document Content Analysis:")
                print("-" * 40)
                print(f"Average Length: {sum(doc_lengths) / len(doc_lengths):.1f} characters")
                print(f"Min Length: {min(doc_lengths)} characters")
                print(f"Max Length: {max(doc_lengths)} characters")
                print(f"Non-empty Documents: {len([d for d in sample_data['documents'] if d])}")
                print()
            
            # Analyze ID patterns
            if sample_data['ids']:
                print(f"🆔 ID Pattern Analysis:")
                print("-" * 40)
                id_samples = sample_data['ids'][:10]
                print(f"Sample IDs: {id_samples}")
                
                # Check for common patterns
                extensions = set()
                for id_str in sample_data['ids']:
                    if '.' in id_str:
                        ext = id_str.split('.')[-1].split('_')[0]
                        extensions.add(ext)
                
                if extensions:
                    print(f"File Extensions Found: {sorted(extensions)}")
                print()
        
        except Exception as e:
            print(f"❌ Error inspecting collection schema: {e}")
    
    def sample_documents(self, collection_name: str, limit: int = 5):
        """Show sample documents from a collection"""
        if collection_name not in self.collections:
            print(f"❌ Collection '{collection_name}' not found")
            return
        
        collection = self.collections[collection_name]
        
        try:
            sample_data = collection.get(
                limit=limit,
                include=['documents', 'metadatas', 'ids']
            )
            
            print(f"\n📖 Sample Documents from '{collection_name}' (showing {limit}):")
            print("=" * 80)
            
            for i, (doc_id, document, metadata) in enumerate(
                zip(sample_data['ids'], sample_data['documents'], sample_data['metadatas']), 1
            ):
                print(f"\n🔹 Document {i}:")
                print(f"ID: {doc_id}")
                print(f"Content ({len(document)} chars): {document[:200]}{'...' if len(document) > 200 else ''}")
                
                if metadata:
                    print("Metadata:")
                    for key, value in metadata.items():
                        print(f"  {key}: {value}")
                print("-" * 40)
        
        except Exception as e:
            print(f"❌ Error sampling documents: {e}")
    
    def search_content(self, collection_name: str, query: str, limit: int = 5):
        """Search for content in a collection"""
        if collection_name not in self.collections:
            print(f"❌ Collection '{collection_name}' not found")
            return
        
        collection = self.collections[collection_name]
        
        try:
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                include=['documents', 'metadatas', 'distances']
            )
            
            print(f"\n🔍 Search Results for '{query}' in '{collection_name}':")
            print("=" * 80)
            
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(
                    zip(results['documents'][0], results['metadatas'][0], results['distances'][0]), 1
                ):
                    similarity = 1 - distance
                    print(f"\n🔹 Result {i} (Similarity: {similarity:.3f}):")
                    print(f"Content: {doc[:300]}{'...' if len(doc) > 300 else ''}")
                    if metadata:
                        print("Metadata:")
                        for key, value in metadata.items():
                            print(f"  {key}: {value}")
                    print("-" * 40)
            else:
                print("No results found.")
        
        except Exception as e:
            print(f"❌ Error searching content: {e}")
    
    def analyze_file_types(self, collection_name: str):
        """Analyze file types and extensions in the collection"""
        if collection_name not in self.collections:
            print(f"❌ Collection '{collection_name}' not found")
            return
        
        collection = self.collections[collection_name]
        
        try:
            # Get all metadata
            all_data = collection.get(include=['metadatas'])
            
            file_types = defaultdict(int)
            extensions = defaultdict(int)
            content_types = defaultdict(int)
            
            for metadata in all_data['metadatas']:
                if metadata:
                    # File extensions
                    if 'file_extension' in metadata:
                        extensions[metadata['file_extension']] += 1
                    
                    # Content types
                    if 'content_type' in metadata:
                        content_types[metadata['content_type']] += 1
                    
                    # File paths for type analysis
                    if 'file_path' in metadata:
                        path = metadata['file_path']
                        if '.' in path:
                            ext = '.' + path.split('.')[-1].lower()
                            file_types[ext] += 1
            
            print(f"\n📊 File Type Analysis for '{collection_name}':")
            print("=" * 60)
            
            if extensions:
                print("📁 File Extensions:")
                for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(all_data['metadatas'])) * 100
                    print(f"  {ext}: {count:,} documents ({percentage:.1f}%)")
                print()
            
            if content_types:
                print("📝 Content Types:")
                for ctype, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(all_data['metadatas'])) * 100
                    print(f"  {ctype}: {count:,} documents ({percentage:.1f}%)")
                print()
        
        except Exception as e:
            print(f"❌ Error analyzing file types: {e}")
    
    def export_sample_data(self, collection_name: str, output_file: str = "sample_data.json"):
        """Export sample data to JSON for detailed inspection"""
        if collection_name not in self.collections:
            print(f"❌ Collection '{collection_name}' not found")
            return
        
        collection = self.collections[collection_name]
        
        try:
            sample_data = collection.get(
                limit=50,
                include=['documents', 'metadatas', 'ids']
            )
            
            export_data = {
                "collection_name": collection_name,
                "total_documents": collection.count(),
                "sample_size": len(sample_data['ids']),
                "documents": []
            }
            
            for doc_id, document, metadata in zip(
                sample_data['ids'], sample_data['documents'], sample_data['metadatas']
            ):
                export_data["documents"].append({
                    "id": doc_id,
                    "content": document,
                    "metadata": metadata
                })
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Sample data exported to: {output_file}")
        
        except Exception as e:
            print(f"❌ Error exporting sample data: {e}")


def main():
    """Main inspection function"""
    print("🔍 ChromaDB Vector Database Inspector")
    print("=" * 60)
    
    inspector = VectorDBInspector()
    
    if not inspector.client:
        print("❌ Cannot connect to database. Exiting.")
        return
    
    # List all collections
    collections = inspector.list_collections()
    
    if not collections:
        print("❌ No collections found in database.")
        return
    
    # Inspect each collection
    for collection_name in collections:
        print(f"\n" + "🔍" * 50)
        print(f"INSPECTING COLLECTION: {collection_name}")
        print("🔍" * 50)
        
        # Schema analysis
        inspector.inspect_collection_schema(collection_name)
        
        # File type analysis
        inspector.analyze_file_types(collection_name)
        
        # Sample documents
        inspector.sample_documents(collection_name, limit=3)
        
        # Sample searches
        sample_queries = [
            "payment transfer money",
            "chat conversation",
            "image photo",
            "audio voice message"
        ]
        
        for query in sample_queries:
            inspector.search_content(collection_name, query, limit=2)
        
        # Export sample data
        output_file = f"sample_{collection_name}.json"
        inspector.export_sample_data(collection_name, output_file)
    
    print(f"\n✅ Inspection complete!")
    print("📊 Check the exported JSON files for detailed data samples.")


if __name__ == "__main__":
    main() 