#!/usr/bin/env python3
"""
Simple Vector Database Inspector for camel_vector_db
Compatible with current ChromaDB API
"""

import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
import json
from collections import defaultdict


def inspect_vector_database():
    """Inspect the vector database schema and content"""
    print("🔍 Vector Database Inspector")
    print("=" * 50)
    
    # Connect to database
    db_path = Path("./data/camel_vector_db")
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return
    
    try:
        client = chromadb.PersistentClient(path=str(db_path))
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        print(f"✅ Connected to database at: {db_path}")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return
    
    # List collections
    collections_info = client.list_collections()
    print(f"\n📁 Collections ({len(collections_info)} total):")
    print("-" * 30)
    
    for i, collection_info in enumerate(collections_info, 1):
        print(f"{i}. {collection_info.name}")
        print(f"   ID: {collection_info.id}")
        
        # Get collection
        try:
            collection = client.get_collection(
                name=collection_info.name,
                embedding_function=embedding_function
            )
            count = collection.count()
            print(f"   Documents: {count:,}")
            
            # Get sample data
            print(f"\n   📊 Analyzing collection '{collection_info.name}'...")
            
            # Sample documents and metadata
            sample_data = collection.get(limit=50, include=['documents', 'metadatas'])
            
            # Analyze metadata schema
            metadata_fields = set()
            file_types = defaultdict(int)
            content_types = defaultdict(int)
            
            for metadata in sample_data['metadatas']:
                if metadata:
                    for key in metadata.keys():
                        metadata_fields.add(key)
                    
                    if 'file_extension' in metadata:
                        file_types[metadata['file_extension']] += 1
                    
                    if 'content_type' in metadata:
                        content_types[metadata['content_type']] += 1
            
            print(f"   📋 Metadata Fields: {sorted(metadata_fields)}")
            
            if file_types:
                print(f"   📁 File Types:")
                for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"      {ext}: {count} files")
            
            if content_types:
                print(f"   📝 Content Types:")
                for ctype, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
                    print(f"      {ctype}: {count} files")
            
            # Sample documents
            print(f"\n   📖 Sample Documents (first 3):")
            for j, (doc, metadata) in enumerate(zip(sample_data['documents'][:3], sample_data['metadatas'][:3]), 1):
                print(f"      📄 Document {j}:")
                print(f"         Content: {doc[:100]}{'...' if len(doc) > 100 else ''}")
                if metadata:
                    key_metadata = {k: v for k, v in metadata.items() if k in ['filename', 'file_extension', 'content_type']}
                    print(f"         Metadata: {key_metadata}")
                print()
            
            # Test search
            print(f"   🔍 Sample Search Results:")
            test_queries = ["payment", "photo", "conversation"]
            
            for query in test_queries:
                try:
                    results = collection.query(
                        query_texts=[query],
                        n_results=2,
                        include=['documents', 'metadatas', 'distances']
                    )
                    
                    if results['documents'] and results['documents'][0]:
                        best_result = results['documents'][0][0]
                        similarity = 1 - results['distances'][0][0]
                        print(f"      '{query}': {best_result[:80]}... (similarity: {similarity:.3f})")
                    else:
                        print(f"      '{query}': No results")
                except Exception as e:
                    print(f"      '{query}': Search error: {e}")
            
        except Exception as e:
            print(f"   ❌ Error accessing collection: {e}")
        
        print()


def export_database_summary():
    """Export a summary of the database to JSON"""
    print("\n📤 Exporting Database Summary...")
    
    db_path = Path("./data/camel_vector_db")
    if not db_path.exists():
        print("❌ Database not found")
        return
    
    try:
        client = chromadb.PersistentClient(path=str(db_path))
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        summary = {
            "database_path": str(db_path),
            "collections": []
        }
        
        collections_info = client.list_collections()
        
        for collection_info in collections_info:
            collection = client.get_collection(
                name=collection_info.name,
                embedding_function=embedding_function
            )
            
            # Get sample data for analysis
            sample_data = collection.get(limit=100, include=['documents', 'metadatas'])
            
            # Analyze metadata
            metadata_schema = {}
            file_types = defaultdict(int)
            
            for metadata in sample_data['metadatas']:
                if metadata:
                    for key, value in metadata.items():
                        if key not in metadata_schema:
                            metadata_schema[key] = type(value).__name__
                        
                        if key == 'file_extension':
                            file_types[value] += 1
            
                                      collection_summary = {
                 "name": collection_info.name,
                 "id": str(collection_info.id),  # Convert UUID to string
                 "document_count": collection.count(),
                 "metadata_schema": metadata_schema,
                 "file_types": dict(file_types),
                 "sample_documents": [
                     {
                         "content": doc[:200],
                         "length": len(doc),
                         "metadata": metadata
                     }
                     for doc, metadata in zip(sample_data['documents'][:5], sample_data['metadatas'][:5])
                 ]
             }
            
            summary["collections"].append(collection_summary)
        
        # Save to file
        output_file = "vector_db_summary.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Database summary exported to: {output_file}")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")


def search_database(query: str, limit: int = 5):
    """Search across all collections in the database"""
    print(f"\n🔍 Searching database for: '{query}'")
    print("=" * 50)
    
    db_path = Path("./data/camel_vector_db")
    if not db_path.exists():
        print("❌ Database not found")
        return
    
    try:
        client = chromadb.PersistentClient(path=str(db_path))
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        collections_info = client.list_collections()
        all_results = []
        
        for collection_info in collections_info:
            collection = client.get_collection(
                name=collection_info.name,
                embedding_function=embedding_function
            )
            
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=limit,
                    include=['documents', 'metadatas', 'distances']
                )
                
                if results['documents'] and results['documents'][0]:
                    for doc, metadata, distance in zip(
                        results['documents'][0], 
                        results['metadatas'][0], 
                        results['distances'][0]
                    ):
                        similarity = 1 - distance
                        all_results.append({
                            "collection": collection_info.name,
                            "content": doc,
                            "metadata": metadata,
                            "similarity": similarity
                        })
            except Exception as e:
                print(f"❌ Error searching {collection_info.name}: {e}")
        
        # Sort by similarity
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        print(f"Found {len(all_results)} results:")
        for i, result in enumerate(all_results[:limit], 1):
            print(f"\n🔹 Result {i} (Similarity: {result['similarity']:.3f})")
            print(f"Collection: {result['collection']}")
            print(f"Content: {result['content'][:200]}{'...' if len(result['content']) > 200 else ''}")
            if result['metadata']:
                key_fields = ['filename', 'file_extension', 'content_type']
                metadata_subset = {k: v for k, v in result['metadata'].items() if k in key_fields}
                if metadata_subset:
                    print(f"Metadata: {metadata_subset}")
            print("-" * 40)
        
    except Exception as e:
        print(f"❌ Search failed: {e}")


if __name__ == "__main__":
    # Run inspection
    inspect_vector_database()
    
    # Export summary
    export_database_summary()
    
    # Example searches
    print("\n" + "🔍" * 30)
    print("SAMPLE SEARCHES:")
    print("🔍" * 30)
    
    sample_queries = [
        "payment transfer money",
        "photo image",
        "meeting appointment"
    ]
    
    for query in sample_queries:
        search_database(query, limit=3) 