#!/usr/bin/env python3
"""
Basic CAMEL AI Example with Project Zohar

This example demonstrates how to use CAMEL AI's core features
integrated with Project Zohar's tool system and agent framework.

Based on CAMEL AI documentation examples but adapted for Project Zohar.
"""

import asyncio
import os
from typing import List

# CAMEL AI imports
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, RoleType
from camel.societies import RolePlaying

# Project Zohar imports
try:
    from zohar.tools.camel_tool_manager import CamelToolManager, ToolEnabledAgent
    from zohar.config.settings import get_settings
    from zohar.utils.logging import get_logger
except ImportError:
    # Fallback for development
    import sys
    sys.path.insert(0, 'src')
    from zohar.tools.camel_tool_manager import CamelToolManager, ToolEnabledAgent
    from zohar.config.settings import get_settings
    from zohar.utils.logging import get_logger

logger = get_logger(__name__)


async def basic_agent_example():
    """Demonstrate basic CAMEL AI agent usage with Project Zohar."""
    print("🤖 Basic CAMEL AI Agent Example")
    print("=" * 50)
    
    settings = get_settings()
    
    # Create model (using Ollama local deployment)
    try:
        model = ModelFactory.create(
            model_platform=ModelPlatformType.OLLAMA,
            model_type="llama3.2",
            url="http://localhost:11434/v1",
            model_config_dict={"temperature": 0.7}
        )
        print("✅ Using Ollama model")
    except Exception as e:
        print(f"⚠️  Ollama not available: {e}")
        return
    
    # Create a simple agent
    system_message = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful AI assistant that can answer questions and help with tasks."
    )
    
    agent = ChatAgent(
        system_message=system_message,
        model=model
    )
    
    # Test conversation
    test_messages = [
        "Hello! What can you help me with?",
        "What is artificial intelligence?",
        "Can you explain machine learning in simple terms?"
    ]
    
    for message in test_messages:
        print(f"\n👤 User: {message}")
        
        user_msg = BaseMessage.make_user_message(
            role_name="User",
            content=message
        )
        
        response = agent.step(user_msg)
        print(f"🤖 Assistant: {response.msg.content}")


async def tool_enabled_agent_example():
    """Demonstrate tool-enabled agent with CAMEL AI tools."""
    print("\n🔧 Tool-Enabled Agent Example")
    print("=" * 50)
    
    # Initialize tool manager
    tool_manager = CamelToolManager()
    await tool_manager.initialize()
    
    available_tools = tool_manager.get_available_tools()
    print(f"✅ Initialized {len(available_tools)} tools")
    
    # Create model
    try:
        model = ModelFactory.create(
            model_platform=ModelPlatformType.OLLAMA,
            model_type="llama3.2",
            url="http://localhost:11434/v1",
            model_config_dict={"temperature": 0.7}
        )
    except Exception as e:
        print(f"⚠️  Ollama not available: {e}")
        return
    
    # Create tool-enabled agent
    agent = ToolEnabledAgent(
        system_message="You are a helpful assistant with access to math and search tools. "
                      "Use the available tools to help answer questions accurately.",
        model=model,
        tool_manager=tool_manager,
        enabled_toolkits=['math', 'search']
    )
    
    print(f"✅ Created agent with {len(agent.tools)} tools")
    
    # Test tool usage
    test_queries = [
        "What is 15 multiplied by 24?",
        "Calculate 100 + 250 + 75",
        "Search for information about CAMEL AI framework"
    ]
    
    for query in test_queries:
        print(f"\n👤 User: {query}")
        try:
            response = await agent.step(query)
            print(f"🤖 Agent: {response.content}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    await tool_manager.shutdown()


async def role_playing_example():
    """Demonstrate CAMEL AI role-playing between two agents."""
    print("\n🎭 Role-Playing Example")
    print("=" * 50)
    
    try:
        model = ModelFactory.create(
            model_platform=ModelPlatformType.OLLAMA,
            model_type="llama3.2",
            url="http://localhost:11434/v1",
            model_config_dict={"temperature": 0.8}
        )
    except Exception as e:
        print(f"⚠️  Ollama not available: {e}")
        return
    
    # Define the task
    task_prompt = """
    Plan a simple Python project structure for a weather application 
    that fetches weather data from an API and displays it to users.
    """
    
    # Create role-playing session
    role_play_session = RolePlaying(
        assistant_role_name="Python Developer",
        user_role_name="Project Manager",
        assistant_agent_kwargs={"model": model},
        user_agent_kwargs={"model": model},
        task_prompt=task_prompt,
        with_task_specify=True,
    )
    
    print("🎭 Starting role-playing session...")
    print("Task: Plan a weather application project structure")
    
    # Initialize the session
    input_msg = role_play_session.init_chat()
    
    # Run a few turns of conversation
    for i in range(3):
        print(f"\n--- Turn {i+1} ---")
        
        assistant_response, user_response = role_play_session.step(input_msg)
        
        print(f"🔵 Project Manager: {user_response.msg.content[:200]}...")
        print(f"🟢 Python Developer: {assistant_response.msg.content[:200]}...")
        
        # Prepare for next turn
        input_msg = assistant_response.msg
        
        # Check if conversation should end
        if role_play_session.assistant_agent.terminated or role_play_session.user_agent.terminated:
            print("🏁 Conversation ended naturally")
            break


async def direct_tool_usage_example():
    """Demonstrate direct usage of CAMEL AI tools without agents."""
    print("\n🛠️  Direct Tool Usage Example")
    print("=" * 50)
    
    # Initialize tool manager
    tool_manager = CamelToolManager()
    await tool_manager.initialize()
    
    # Show available tools
    tools = tool_manager.get_available_tools()
    print("📋 Available Tools:")
    for tool in tools[:5]:  # Show first 5 tools
        print(f"  - {tool['name']}: {tool['description']}")
    
    # Test math tools
    print("\n🧮 Testing Math Tools:")
    
    # Addition
    result = await tool_manager.execute_tool('math_add', {'a': 42, 'b': 58})
    if result['success']:
        print(f"  42 + 58 = {result['result']}")
    
    # Multiplication
    result = await tool_manager.execute_tool('math_mul', {'a': 7, 'b': 8})
    if result['success']:
        print(f"  7 × 8 = {result['result']}")
    
    # Test search tools (if available)
    print("\n🔍 Testing Search Tools:")
    
    try:
        result = await tool_manager.execute_tool(
            'search_search_wiki',
            {'query': 'artificial intelligence'}
        )
        if result['success']:
            print(f"  Wikipedia search result: {result['result'][:100]}...")
        else:
            print(f"  Search failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"  Search error: {e}")
    
    # Show execution statistics
    stats = tool_manager.get_execution_stats()
    print(f"\n📊 Execution Stats:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Successful: {stats['successful_calls']}")
    print(f"  Failed: {stats['failed_calls']}")
    
    await tool_manager.shutdown()


async def main():
    """Run all examples."""
    print("🚀 CAMEL AI Integration Examples for Project Zohar")
    print("=" * 60)
    
    examples = [
        ("Basic Agent", basic_agent_example),
        ("Tool-Enabled Agent", tool_enabled_agent_example),
        ("Role-Playing", role_playing_example),
        ("Direct Tool Usage", direct_tool_usage_example),
    ]
    
    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"❌ {name} example failed: {e}")
            logger.error(f"{name} example error: {e}", exc_info=True)
        
        print("\n" + "=" * 60)
    
    print("🎉 All examples completed!")
    print("\n💡 Next Steps:")
    print("1. Try running individual examples")
    print("2. Experiment with different models and tools")
    print("3. Create your own multi-agent workflows")
    print("4. Explore CAMEL AI documentation: https://docs.camel-ai.org/")


if __name__ == "__main__":
    asyncio.run(main()) 