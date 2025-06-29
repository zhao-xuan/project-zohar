#!/usr/bin/env python3
"""
Vector Database Inspector for camel_vector_db
"""

import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
import json
from collections import defaultdict


def inspect_database():
    """Inspect the vector database"""
    print("🔍 ChromaDB Vector Database Inspector")
    print("=" * 50)
    
    db_path = Path("./data/camel_vector_db")
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return
    
    try:
        client = chromadb.PersistentClient(path=str(db_path))
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        print(f"✅ Connected to database")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return
    
    # List collections
    collections = client.list_collections()
    print(f"\n📁 Collections: {len(collections)}")
    
    for collection_info in collections:
        print(f"\n🔹 Collection: {collection_info.name}")
        print(f"   ID: {str(collection_info.id)}")
        
        try:
            collection = client.get_collection(
                name=collection_info.name,
                embedding_function=embedding_function
            )
            count = collection.count()
            print(f"   Documents: {count:,}")
            
            # Sample data
            sample = collection.get(limit=20, include=['documents', 'metadatas'])
            
            # Analyze metadata
            metadata_fields = set()
            file_types = defaultdict(int)
            
            for metadata in sample['metadatas']:
                if metadata:
                    metadata_fields.update(metadata.keys())
                    if 'file_extension' in metadata:
                        file_types[metadata['file_extension']] += 1
            
            print(f"   Metadata Fields: {sorted(metadata_fields)}")
            print(f"   File Types: {dict(file_types)}")
            
            # Sample documents
            print(f"   \n📄 Sample Documents:")
            for i, (doc, meta) in enumerate(zip(sample['documents'][:3], sample['metadatas'][:3]), 1):
                print(f"   {i}. {doc[:100]}...")
                if meta:
                    print(f"      Meta: {meta.get('filename', 'N/A')} ({meta.get('file_extension', 'N/A')})")
            
            # Test searches
            queries = ["payment", "photo", "meeting"]
            print(f"   \n🔍 Search Tests:")
            
            for query in queries:
                try:
                    results = collection.query(
                        query_texts=[query],
                        n_results=1,
                        include=['documents', 'distances']
                    )
                    if results['documents'] and results['documents'][0]:
                        doc = results['documents'][0][0]
                        similarity = 1 - results['distances'][0][0]
                        print(f"   '{query}': {doc[:60]}... (sim: {similarity:.3f})")
                except Exception as e:
                    print(f"   '{query}': Error - {e}")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")


def search_database(query: str):
    """Search the database"""
    print(f"\n🔍 Searching for: '{query}'")
    print("-" * 30)
    
    db_path = Path("./data/camel_vector_db")
    if not db_path.exists():
        print("❌ Database not found")
        return
    
    try:
        client = chromadb.PersistentClient(path=str(db_path))
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        collections = client.list_collections()
        for collection_info in collections:
            collection = client.get_collection(
                name=collection_info.name,
                embedding_function=embedding_function
            )
            
            results = collection.query(
                query_texts=[query],
                n_results=3,
                include=['documents', 'metadatas', 'distances']
            )
            
            if results['documents'] and results['documents'][0]:
                for i, (doc, meta, dist) in enumerate(zip(
                    results['documents'][0], 
                    results['metadatas'][0], 
                    results['distances'][0]
                ), 1):
                    similarity = 1 - dist
                    print(f"{i}. {doc[:150]}...")
                    print(f"   Similarity: {similarity:.3f}")
                    if meta and 'filename' in meta:
                        print(f"   File: {meta['filename']}")
                    print()
    
    except Exception as e:
        print(f"❌ Search error: {e}")


if __name__ == "__main__":
    inspect_database()
    
    # Sample searches
    print("\n" + "="*50)
    print("SAMPLE SEARCHES")
    print("="*50)
    
    for query in ["payment transfer", "photo image", "meeting appointment"]:
        search_database(query) 