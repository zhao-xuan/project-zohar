#!/usr/bin/env python3
"""
Data Digestion Demo

Demonstrates the intelligent data discovery, analysis, and structure generation
capabilities of Project Zohar's data digestion system.
"""

import asyncio
import json
import tempfile
import os
from pathlib import Path
from typing import Dict, Any

# Create sample data files for demonstration
def create_sample_data(temp_dir: Path) -> Dict[str, str]:
    """Create sample files to demonstrate data digestion."""
    sample_files = {}
    
    # CSV file
    csv_content = """Name,Age,City,Country,Occupation
John Doe,30,New York,USA,Engineer
Jane Smith,25,London,UK,Designer
Pedro Garcia,35,Madrid,Spain,Teacher
Marie Dupont,28,Paris,France,Doctor
Hans Mueller,42,Berlin,Germany,Lawyer"""
    
    csv_file = temp_dir / "users.csv"
    csv_file.write_text(csv_content)
    sample_files['csv'] = str(csv_file)
    
    # JSON file
    json_content = {
        "products": [
            {"id": 1, "name": "Laptop", "price": 999.99, "category": "Electronics"},
            {"id": 2, "name": "Book", "price": 19.99, "category": "Education"},
            {"id": 3, "name": "Coffee", "price": 4.50, "category": "Food"}
        ],
        "metadata": {
            "version": "1.0",
            "created": "2024-01-01",
            "source": "inventory_system"
        }
    }
    
    json_file = temp_dir / "products.json"
    json_file.write_text(json.dumps(json_content, indent=2))
    sample_files['json'] = str(json_file)
    
    # Text/Log file
    log_content = """2024-01-01 09:00:01 INFO Application started
2024-01-01 09:00:15 DEBUG Loading configuration
2024-01-01 09:00:30 INFO Database connection established
2024-01-01 09:01:00 WARN Memory usage high: 85%
2024-01-01 09:01:15 ERROR Failed to process user request: timeout
2024-01-01 09:01:30 INFO Error recovery successful
2024-01-01 09:02:00 DEBUG Processing 150 pending requests"""
    
    log_file = temp_dir / "application.log"
    log_file.write_text(log_content)
    sample_files['log'] = str(log_file)
    
    # Markdown file
    md_content = """# Project Documentation

## Overview
This is a sample documentation file to demonstrate markdown parsing.

## Features
- Feature 1: Data processing
- Feature 2: AI integration
- Feature 3: Vector search

## Installation
```bash
pip install project-zohar
```

## Configuration
Set up your environment variables:
- `API_KEY`: Your API key
- `DATABASE_URL`: Database connection string

## Usage
Start the application with:
```python
from zohar import ZoharApp
app = ZoharApp()
app.run()
```"""
    
    md_file = temp_dir / "README.md"
    md_file.write_text(md_content)
    sample_files['markdown'] = str(md_file)
    
    # XML file
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<library>
    <book id="1">
        <title>The AI Revolution</title>
        <author>Dr. Smith</author>
        <year>2024</year>
        <genre>Technology</genre>
    </book>
    <book id="2">
        <title>Data Science Handbook</title>
        <author>Prof. Jones</author>
        <year>2023</year>
        <genre>Education</genre>
    </book>
</library>"""
    
    xml_file = temp_dir / "library.xml"
    xml_file.write_text(xml_content)
    sample_files['xml'] = str(xml_file)
    
    return sample_files


async def run_digestion_demo():
    """Run the complete data digestion demonstration."""
    print("🤖 Project Zohar - Data Digestion Demo")
    print("=" * 50)
    
    # Create temporary directory with sample data
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"📁 Creating sample data in: {temp_path}")
        
        sample_files = create_sample_data(temp_path)
        print(f"✅ Created {len(sample_files)} sample files:")
        for file_type, file_path in sample_files.items():
            print(f"   - {file_type}: {Path(file_path).name}")
        
        print("\n" + "=" * 50)
        print("🔍 Starting Data Digestion Process")
        print("=" * 50)
        
        try:
            # Import the digestion manager
            from zohar.services.data_digestion import DigestionManager
            
            # Initialize digestion manager
            dm = DigestionManager()
            
            # Phase 1: Start digestion
            print("\n📋 Phase 1: File Discovery")
            session_id = await dm.start_digestion(str(temp_path), max_files=20)
            print(f"✅ Started digestion session: {session_id}")
            
            # Wait a moment for processing
            await asyncio.sleep(2)
            
            # Check status
            status = dm.get_session_status(session_id)
            print(f"📊 Session Status: {status['status']}")
            print(f"📁 Files Discovered: {status['files_discovered']}")
            
            # Wait for analysis to complete
            print("\n🔬 Phase 2: Waiting for content analysis...")
            max_wait = 30  # Maximum wait time in seconds
            wait_time = 0
            
            while status['status'] in ['discovering', 'analyzing'] and wait_time < max_wait:
                await asyncio.sleep(2)
                wait_time += 2
                status = dm.get_session_status(session_id)
                print(f"   Status: {status['status']} ({wait_time}s)")
            
            print(f"✅ Analysis Complete: {status['files_analyzed']} files analyzed")
            
            # Phase 3: Check structure recommendation
            print("\n🏗️  Phase 3: Structure Generation")
            if status['status'] in ['structuring', 'feedback_required', 'completed']:
                recommendation = dm.get_structure_recommendation(session_id)
                if recommendation:
                    print(f"✅ Structure Generated: {recommendation.structure.name}")
                    print(f"🎯 Confidence: {recommendation.confidence:.2f}")
                    print(f"📝 Reasoning: {recommendation.reasoning}")
                    
                    if recommendation.structure.fields:
                        print(f"📋 Fields ({len(recommendation.structure.fields)}):")
                        for field in recommendation.structure.fields[:5]:  # Show first 5 fields
                            print(f"   - {field.name} ({field.type}): {field.description}")
                        if len(recommendation.structure.fields) > 5:
                            print(f"   ... and {len(recommendation.structure.fields) - 5} more")
                    
                    if recommendation.user_feedback_required:
                        print("⚠️  User feedback required:")
                        for feedback_item in recommendation.user_feedback_required:
                            print(f"   - {feedback_item}")
                else:
                    print("⚠️  No structure recommendation available yet")
            
            # Phase 4: Show final results
            print("\n📊 Phase 4: Final Results")
            final_status = dm.get_session_status(session_id)
            
            print(f"🎯 Final Status: {final_status['status']}")
            print(f"📁 Output Files:")
            for file_type, file_path in final_status.get('output_files', {}).items():
                print(f"   - {file_type}: {file_path}")
            
            # Show some sample analysis results if available
            if 'analysis' in final_status.get('output_files', {}):
                try:
                    analysis_path = final_status['output_files']['analysis']
                    if os.path.exists(analysis_path):
                        with open(analysis_path, 'r') as f:
                            analysis_data = json.load(f)
                        
                        print(f"\n📈 Analysis Summary:")
                        print(f"   - Files Analyzed: {analysis_data.get('files_analyzed', 0)}")
                        
                        format_dist = analysis_data.get('format_distribution', {})
                        if format_dist:
                            print(f"   - Format Distribution:")
                            for fmt, count in format_dist.items():
                                print(f"     • {fmt}: {count} files")
                
                except Exception as e:
                    print(f"   Could not read analysis file: {e}")
            
            # Cleanup
            print(f"\n🧹 Cleaning up session: {session_id}")
            dm.cleanup_session(session_id, keep_outputs=False)
            
        except ImportError as e:
            print(f"❌ Import Error: {e}")
            print("📝 Make sure all dependencies are installed:")
            print("   pip install -e .")
            return False
        
        except Exception as e:
            print(f"❌ Error during digestion: {e}")
            return False
    
    print("\n" + "=" * 50)
    print("✅ Data Digestion Demo Complete!")
    print("=" * 50)
    
    print("\n🎯 What happened:")
    print("1. 📁 Discovered and analyzed multiple file formats")
    print("2. 🔍 Detected file types using magic bytes and content analysis")
    print("3. 📊 Generated comprehensive content descriptions")
    print("4. 🏗️  Created optimized data structure recommendations")
    print("5. 🤖 Used AI to understand patterns and relationships")
    
    print("\n💡 Next Steps:")
    print("- Use 'make digest-data' to process your own data")
    print("- Check 'make digest-status' to monitor progress")
    print("- Provide feedback to refine data structures")
    print("- Create vector databases for semantic search")
    
    return True


def main():
    """Main demo function."""
    try:
        # Check if we're in an async context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context, create task
            task = asyncio.create_task(run_digestion_demo())
            return task
        else:
            # Run in new event loop
            return asyncio.run(run_digestion_demo())
    except RuntimeError:
        # No event loop, create new one
        return asyncio.run(run_digestion_demo())


if __name__ == "__main__":
    success = main()
    if not success:
        exit(1) 