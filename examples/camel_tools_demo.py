#!/usr/bin/env python3
"""
CAMEL AI Tools Demo for Project Zohar

This script demonstrates how to use CAMEL AI's native toolkit system
with Project Zohar's agents for tool calling functionality.
"""

import asyncio
import json
from typing import Dict, Any

from camel.models import ModelFactory
from camel.types import ModelPlatformType
from camel.messages import BaseMessage

from zohar.tools.camel_tool_manager import CamelToolManager, ToolEnabledAgent
from zohar.config.settings import get_settings
from zohar.utils.logging import get_logger

logger = get_logger(__name__)


async def demo_basic_tool_usage():
    """Demonstrate basic tool usage with CAMEL AI."""
    print("🔧 Initializing CAMEL AI Tool Manager...")
    
    # Initialize tool manager
    tool_manager = CamelToolManager()
    success = await tool_manager.initialize()
    
    if not success:
        print("❌ Failed to initialize tool manager")
        return
    
    print(f"✅ Tool manager initialized with {len(tool_manager.available_tools)} tools")
    
    # List available tools
    print("\n📋 Available Tools:")
    tools = tool_manager.get_available_tools()
    for i, tool in enumerate(tools[:10]):  # Show first 10 tools
        print(f"  {i+1}. {tool['name']} ({tool['toolkit']})")
        print(f"     {tool['description']}")
        print()
    
    # Test a simple tool execution
    print("🧮 Testing Math Tool...")
    try:
        result = await tool_manager.execute_tool(
            tool_name="math_add",
            parameters={"a": 15, "b": 27}
        )
        print(f"✅ Math result: {result}")
    except Exception as e:
        print(f"❌ Math tool error: {e}")
    
    # Test search tool
    print("\n🔍 Testing Search Tool...")
    try:
        result = await tool_manager.execute_tool(
            tool_name="search_duckduckgo",
            parameters={"query": "CAMEL AI framework"}
        )
        print(f"✅ Search result: {result}")
    except Exception as e:
        print(f"❌ Search tool error: {e}")
    
    # Get execution statistics
    stats = tool_manager.get_execution_stats()
    print(f"\n📊 Execution Statistics:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Successful: {stats['successful_calls']}")
    print(f"  Failed: {stats['failed_calls']}")
    
    await tool_manager.shutdown()


async def demo_tool_enabled_agent():
    """Demonstrate tool-enabled agent functionality."""
    print("\n🤖 Initializing Tool-Enabled Agent...")
    
    settings = get_settings()
    
    # Initialize tool manager
    tool_manager = CamelToolManager()
    success = await tool_manager.initialize()
    
    if not success:
        print("❌ Failed to initialize tool manager")
        return
    
    # Create model
    try:
        # Try to use local Ollama model
        model = ModelFactory.create(
            model_platform=ModelPlatformType.OLLAMA,
            model_type="llama3.2",
            url="http://localhost:11434/v1",
            model_config_dict={"temperature": 0.7}
        )
        print("✅ Using Ollama model")
    except Exception as e:
        print(f"⚠️  Ollama not available, using mock model: {e}")
        # For demo purposes, we'll create a simple mock
        model = None
    
    if model is None:
        print("❌ No model available for agent demo")
        return
    
    # Create tool-enabled agent
    agent = ToolEnabledAgent(
        system_message="You are a helpful assistant with access to various tools. "
                      "Use the available tools to help answer questions and solve problems.",
        model=model,
        tool_manager=tool_manager,
        enabled_toolkits=['math', 'search', 'weather']
    )
    
    print(f"✅ Agent created with {len(agent.tools)} tools")
    
    # Test some queries
    test_queries = [
        "What is 123 + 456?",
        "Search for information about artificial intelligence",
        "What's the weather like today?",
    ]
    
    for query in test_queries:
        print(f"\n👤 User: {query}")
        try:
            response = await agent.step(query)
            print(f"🤖 Agent: {response.content}")
        except Exception as e:
            print(f"❌ Agent error: {e}")
    
    await tool_manager.shutdown()


async def demo_toolkit_management():
    """Demonstrate toolkit management features."""
    print("\n🔧 Toolkit Management Demo...")
    
    # Initialize tool manager
    tool_manager = CamelToolManager()
    success = await tool_manager.initialize()
    
    if not success:
        print("❌ Failed to initialize tool manager")
        return
    
    # Show available toolkits
    toolkit_names = tool_manager.get_toolkit_names()
    print(f"📦 Available Toolkits: {toolkit_names}")
    
    # Show tools by category
    categories = ['code', 'math', 'search', 'communication', 'creative']
    for category in categories:
        tools = tool_manager.get_tools_by_category(category)
        print(f"\n📂 {category.title()} Tools ({len(tools)} tools):")
        for tool in tools:
            print(f"  - {tool['name']}")
    
    # Search for tools
    print("\n🔍 Searching for 'calculate' tools:")
    search_results = tool_manager.search_tools("calculate")
    for tool in search_results:
        print(f"  - {tool['name']}: {tool['description']}")
    
    await tool_manager.shutdown()


async def demo_agent_with_specific_toolkits():
    """Demo agent with specific toolkit configurations."""
    print("\n🎯 Agent with Specific Toolkits Demo...")
    
    settings = get_settings()
    
    # Initialize tool manager
    tool_manager = CamelToolManager()
    success = await tool_manager.initialize()
    
    if not success:
        print("❌ Failed to initialize tool manager")
        return
    
    # Create different agents with different toolkit configurations
    agent_configs = [
        {
            "name": "Math Agent",
            "toolkits": ["math"],
            "message": "You are a math specialist. Use math tools to solve problems."
        },
        {
            "name": "Research Agent", 
            "toolkits": ["search", "arxiv"],
            "message": "You are a research assistant. Use search and research tools to find information."
        },
        {
            "name": "Code Agent",
            "toolkits": ["code_execution"],
            "message": "You are a coding assistant. Use code execution tools to help with programming."
        }
    ]
    
    for config in agent_configs:
        print(f"\n🤖 Creating {config['name']}...")
        
        # Check if we have the required toolkits
        available_toolkits = set(tool_manager.get_toolkit_names())
        requested_toolkits = set(config['toolkits'])
        missing_toolkits = requested_toolkits - available_toolkits
        
        if missing_toolkits:
            print(f"⚠️  Missing toolkits: {missing_toolkits}")
            continue
        
        # Show tools for this agent
        tools = []
        for toolkit in config['toolkits']:
            toolkit_tools = tool_manager.get_available_tools(toolkit)
            tools.extend(toolkit_tools)
        
        print(f"   Available tools: {[t['name'] for t in tools]}")
    
    await tool_manager.shutdown()


async def main():
    """Main demo function."""
    print("🚀 CAMEL AI Tools Demo for Project Zohar")
    print("=" * 50)
    
    demos = [
        ("Basic Tool Usage", demo_basic_tool_usage),
        ("Tool-Enabled Agent", demo_tool_enabled_agent),
        ("Toolkit Management", demo_toolkit_management),
        ("Agent with Specific Toolkits", demo_agent_with_specific_toolkits),
    ]
    
    for name, demo_func in demos:
        print(f"\n{'='*20} {name} {'='*20}")
        try:
            await demo_func()
        except Exception as e:
            print(f"❌ Demo '{name}' failed: {e}")
            logger.error(f"Demo error: {e}", exc_info=True)
        
        print(f"\n{'='*50}")
    
    print("\n🎉 Demo completed!")


if __name__ == "__main__":
    asyncio.run(main()) 