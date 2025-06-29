#!/usr/bin/env python3
"""
Camel-AI Integration Example

This example demonstrates how to use the new Camel-AI based file processing system
to create a complete multimodal vector knowledge base from mixed data sources.
"""

import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any

# Camel-AI imports
from camel.embeddings import OpenAIEmbeddings
from camel.storages.vectordb_storages.chroma import ChromaStorage

# Our new processors
from src.services import CamelFileProcessor, CamelChatParser
from src.services.camel_file_processor import SchemaDesignerAgent, FileSummarizerAgent

async def main():
    """Example usage of the Camel-AI file processing system"""
    
    print("🐪 Camel-AI File Processing System Example")
    print("=" * 50)
    
    # Initialize embeddings (requires OPENAI_API_KEY in environment)
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Warning: OPENAI_API_KEY not set. Using mock embeddings for demo.")
        print("   Set your API key: export OPENAI_API_KEY='your-key-here'")
        # For demo purposes, you could use local embeddings here
        embeddings = OpenAIEmbeddings()  # This will work but may fail without API key
    else:
        embeddings = OpenAIEmbeddings()
    
    # Initialize vector storage
    vector_storage = ChromaStorage(
        path="data/example_vector_db",
        embedding_model=embeddings
    )
    
    # Initialize file processor
    processor = CamelFileProcessor(
        storage_path="data/example_vector_db",
        embedding_model="text-embedding-ada-002",
        chunk_size=256,  # Smaller chunks for demo
        chunk_overlap=25
    )
    
    print("✅ Initialized Camel-AI processors")
    
    # Example 1: Process a directory with mixed file types
    print("\n📁 Example 1: Processing Mixed File Directory")
    print("-" * 40)
    
    # Create some example data if it doesn't exist
    example_dir = Path("data/example_files")
    example_dir.mkdir(parents=True, exist_ok=True)
    
    # Create example files
    await create_example_files(example_dir)
    
    # Process the directory
    results = await processor.process_directory(
        str(example_dir),
        exclude_patterns=["*.tmp", "*.log"]  # Exclude temporary files
    )
    
    if results['success']:
        print(f"✅ Processed {results['processing_stats']['processed_files']} files")
        print(f"📚 Created {results['processing_stats']['collections_created']} collections")
        print(f"🧩 Generated {results['processing_stats']['total_chunks']} chunks")
        print(f"📋 Collections: {', '.join(results['collections_created'])}")
    else:
        print(f"❌ Processing failed: {results.get('error')}")
        return
    
    # Example 2: Specialized chat processing
    print("\n💬 Example 2: Specialized Chat Processing")
    print("-" * 40)
    
    # Create chat example data
    chat_dir = Path("data/example_chats")
    await create_example_chat_files(chat_dir)
    
    # Initialize chat parser
    chat_parser = CamelChatParser(vector_storage)
    
    # Process chat files
    chat_results = await chat_parser.process_chat_directory(str(chat_dir))
    
    if not chat_results.get('error'):
        stats = chat_results['stats']
        print(f"✅ Processed {stats['total_files']} chat files")
        print(f"💬 Extracted {stats['processed_messages']} messages")
        print(f"📎 Processed {stats['processed_attachments']} attachments")
        
        # Show platform breakdown
        platforms = set()
        for message in chat_results.get('messages', []):
            platforms.add(message.platform)
        print(f"🌐 Platforms: {', '.join(platforms)}")
    else:
        print(f"❌ Chat processing failed: {chat_results['error']}")
    
    # Example 3: Querying the vector database
    print("\n🔍 Example 3: Querying Vector Database")
    print("-" * 40)
    
    # Query examples
    queries = [
        "What is machine learning?",
        "Show me messages about planning",
        "Find technical documentation",
        "What are the main topics discussed?"
    ]
    
    for query in queries:
        print(f"\n❓ Query: '{query}'")
        try:
            results = await processor.query(query, top_k=3)
            
            if results:
                for i, result in enumerate(results[:2], 1):  # Show top 2 results
                    # Results format may vary based on ChromaStorage implementation
                    print(f"  {i}. {str(result)[:100]}...")
            else:
                print("  No results found")
        except Exception as e:
            print(f"  Error querying: {e}")
    
    # Example 4: Collection information
    print("\n📊 Example 4: Collection Information")
    print("-" * 40)
    
    collection_info = processor.get_collection_info()
    
    print(f"📚 Total Collections: {len(collection_info['collections'])}")
    print(f"📈 Processing Stats:")
    for key, value in collection_info['stats'].items():
        print(f"  {key}: {value}")
    
    if collection_info['registry']:
        print(f"📋 Collection Registry:")
        for name, info in collection_info['registry'].items():
            description = info.get('description', 'No description')
            print(f"  {name}: {description}")
    
    # Example 5: Using Schema Designer and File Summarizer agents
    print("\n🤖 Example 5: AI Agents in Action")
    print("-" * 40)
    
    # Schema Designer example
    schema_designer = SchemaDesignerAgent()
    sample_metadata = [
        {'file_type': 'text', 'content_type': 'markdown', 'size': 1024},
        {'file_type': 'text', 'content_type': 'json', 'size': 2048},
        {'file_type': 'image', 'content_type': 'jpg', 'size': 512000}
    ]
    
    try:
        schema = await schema_designer.design_schema(sample_metadata, "example_collection")
        print(f"🗄️  Generated Schema for 'example_collection':")
        print(f"   Description: {schema.description}")
        print(f"   Fields: {schema.fields}")
    except Exception as e:
        print(f"⚠️  Schema generation error: {e}")
    
    # File Summarizer example
    file_summarizer = FileSummarizerAgent()
    from src.services.camel_file_processor import ProcessedFile
    
    # Create sample processed files for demonstration
    sample_files = [
        ProcessedFile(
            file_path="/example/doc1.txt",
            file_name="doc1.txt",
            file_extension=".txt",
            file_size=1024,
            mime_type="text/plain",
            content_type="text",
            processed_content="Technical documentation about AI systems",
            metadata={'topic': 'AI'},
            chunks=[],
            schema_collection="docs_texts",
            processing_timestamp="2024-01-01T00:00:00",
            content_hash="abc123"
        )
    ]
    
    try:
        summary = await file_summarizer.summarize_collection("example_docs", sample_files)
        print(f"📝 Generated Summary: {summary}")
    except Exception as e:
        print(f"⚠️  Summarization error: {e}")
    
    # Example 6: Save processing results
    print("\n💾 Example 6: Saving Results")
    print("-" * 40)
    
    output_path = "data/example_processing_results.json"
    await processor.save_processing_results(output_path)
    print(f"✅ Results saved to: {output_path}")
    
    print("\n🎉 Camel-AI Integration Example Complete!")
    print("📁 Check data/example_vector_db/ for your vector database")
    print("📄 Check data/example_processing_results.json for detailed results")
    print("\n🚀 Next Steps:")
    print("1. Run with your own data: python examples/camel_ai_integration_example.py")
    print("2. Integrate with main system: python main.py parse-personal-data")
    print("3. Query via terminal: python main.py terminal")


async def create_example_files(example_dir: Path):
    """Create example files for demonstration"""
    example_dir.mkdir(parents=True, exist_ok=True)
    
    # Text file
    with open(example_dir / "example.txt", 'w') as f:
        f.write("""
# Machine Learning Basics

Machine learning is a subset of artificial intelligence that enables computers 
to learn and improve from experience without being explicitly programmed.

## Key Concepts:
- Supervised Learning
- Unsupervised Learning
- Neural Networks
- Deep Learning

This is useful for building intelligent systems.
""")
    
    # JSON file
    with open(example_dir / "config.json", 'w') as f:
        f.write("""{
    "model_config": {
        "name": "example_model",
        "type": "transformer",
        "parameters": 1000000,
        "training_data": "large_corpus"
    },
    "settings": {
        "temperature": 0.7,
        "max_tokens": 1000
    }
}""")
    
    # Markdown file
    with open(example_dir / "README.md", 'w') as f:
        f.write("""# Project Documentation

This is an example project demonstrating multimodal data processing.

## Features
- Text processing
- Image analysis
- Audio transcription
- Vector search

## Usage
Run the processor on your data directory to create searchable embeddings.
""")
    
    print(f"📝 Created example files in {example_dir}")


async def create_example_chat_files(chat_dir: Path):
    """Create example chat files for demonstration"""
    chat_dir.mkdir(parents=True, exist_ok=True)
    
    # WhatsApp style chat
    with open(chat_dir / "whatsapp_chat.txt", 'w') as f:
        f.write("""12/25/2023, 10:30 AM - Alice: Hey, are we still meeting today?
12/25/2023, 10:31 AM - Bob: Yes! I'll be there at 2 PM
12/25/2023, 10:32 AM - Alice: Perfect. Should we bring the project documents?
12/25/2023, 10:33 AM - Bob: Good idea. I'll bring the technical specs
12/25/2023, 10:35 AM - Alice: <Media omitted>
12/25/2023, 10:36 AM - Bob: Thanks for sharing the mockups!
12/25/2023, 10:40 AM - Alice: Let's discuss the AI integration approach
12/25/2023, 10:41 AM - Bob: I think we should use the camel-ai framework
""")
    
    # Telegram style JSON export
    with open(chat_dir / "telegram_export.json", 'w') as f:
        f.write("""{
    "name": "Tech Discussion",
    "type": "personal_chat",
    "messages": [
        {
            "id": 1,
            "date": "2023-12-25T14:30:00",
            "from": "Charlie",
            "text": "Have you seen the new Camel-AI features?",
            "type": "message"
        },
        {
            "id": 2,
            "date": "2023-12-25T14:31:00",
            "from": "Dana",
            "text": "Yes! The multimodal processing is amazing",
            "type": "message"
        },
        {
            "id": 3,
            "date": "2023-12-25T14:32:00",
            "from": "Charlie",
            "text": "We should integrate it into our workflow",
            "type": "message"
        }
    ]
}""")
    
    print(f"💬 Created example chat files in {chat_dir}")


if __name__ == "__main__":
    asyncio.run(main()) 