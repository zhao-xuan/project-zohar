#!/usr/bin/env python3
"""
Multi-Agent Framework Demo for Project Zohar.

This script demonstrates the multi-agent framework with detailed logging
of tool execution processes and model communication.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from zohar.core.multi_agent.multi_agent_manager import MultiAgentManager
from zohar.core.multi_agent.agent_types import AgentRole, AgentCapability
from zohar.utils.logging import setup_logging

# Setup detailed logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_basic_multi_agent():
    """Demo basic multi-agent interaction."""
    print("\n" + "="*60)
    print("🤖 BASIC MULTI-AGENT INTERACTION DEMO")
    print("="*60)
    
    # Initialize multi-agent manager
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        # Test basic conversation
        query = "Hello! Can you help me with a simple task?"
        print(f"\n👤 User: {query}")
        
        response = await manager.process_query(query)
        print(f"\n🤖 Response: {response}")
        
    finally:
        await manager.shutdown()


async def demo_tool_execution_process():
    """Demo detailed tool execution process with logging."""
    print("\n" + "="*60)
    print("🛠️  DETAILED TOOL EXECUTION PROCESS DEMO")
    print("="*60)
    
    # Initialize multi-agent manager
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        # Test math calculation to show tool execution process
        query = "Calculate 15 * 23 for me"
        print(f"\n👤 User: {query}")
        print(f"\n🔍 This will demonstrate:")
        print(f"   • Task analysis and tool selection")
        print(f"   • Parameter extraction")
        print(f"   • Tool execution with model communication")
        print(f"   • Result synthesis and response")
        
        response = await manager.process_query(query)
        print(f"\n🤖 Final Response: {response}")
        
        # Show execution log
        tool_executor = manager.get_agent_by_role(AgentRole.TOOL_EXECUTOR)
        if tool_executor:
            execution_log = tool_executor.get_execution_log(limit=10)
            print(f"\n📋 Recent Execution Log:")
            for entry in execution_log:
                print(f"   [{entry['timestamp']}] {entry['step']}: {entry['data']}")
        
    finally:
        await manager.shutdown()


async def demo_search_and_synthesis():
    """Demo search and result synthesis process."""
    print("\n" + "="*60)
    print("🔍 SEARCH AND SYNTHESIS DEMO")
    print("="*60)
    
    # Initialize multi-agent manager
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        # Test search functionality
        query = "Search for information about artificial intelligence trends in 2024"
        print(f"\n👤 User: {query}")
        print(f"\n🔍 This will demonstrate:")
        print(f"   • Search tool selection")
        print(f"   • Web search execution")
        print(f"   • Result processing and synthesis")
        
        response = await manager.process_query(query)
        print(f"\n🤖 Final Response: {response}")
        
    finally:
        await manager.shutdown()


async def demo_code_execution():
    """Demo code execution process."""
    print("\n" + "="*60)
    print("💻 CODE EXECUTION DEMO")
    print("="*60)
    
    # Initialize multi-agent manager
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        # Test code execution
        query = "Write a Python function to calculate the factorial of a number and test it with 5"
        print(f"\n👤 User: {query}")
        print(f"\n🔍 This will demonstrate:")
        print(f"   • Code generation and execution")
        print(f"   • Tool calling for code execution")
        print(f"   • Result validation and presentation")
        
        response = await manager.process_query(query)
        print(f"\n🤖 Final Response: {response}")
        
    finally:
        await manager.shutdown()


async def demo_weather_integration():
    """Demo weather tool integration."""
    print("\n" + "="*60)
    print("🌤️  WEATHER INTEGRATION DEMO")
    print("="*60)
    
    # Initialize multi-agent manager
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        # Test weather functionality
        query = "What's the current weather like?"
        print(f"\n👤 User: {query}")
        print(f"\n🔍 This will demonstrate:")
        print(f"   • Weather tool selection")
        print(f"   • API call execution")
        print(f"   • Weather data processing")
        
        response = await manager.process_query(query)
        print(f"\n🤖 Final Response: {response}")
        
    finally:
        await manager.shutdown()


async def demo_complex_multi_tool_task():
    """Demo complex task requiring multiple tools."""
    print("\n" + "="*60)
    print("🎯 COMPLEX MULTI-TOOL TASK DEMO")
    print("="*60)
    
    # Initialize multi-agent manager
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        # Test complex task
        query = "Search for the latest AI news, then calculate how many days it's been since the first AI paper was published in 1956"
        print(f"\n👤 User: {query}")
        print(f"\n🔍 This will demonstrate:")
        print(f"   • Multiple tool coordination")
        print(f"   • Search and math tool combination")
        print(f"   • Result synthesis from multiple sources")
        
        response = await manager.process_query(query)
        print(f"\n🤖 Final Response: {response}")
        
    finally:
        await manager.shutdown()


async def demo_agent_capabilities():
    """Demo different agent capabilities."""
    print("\n" + "="*60)
    print("🎭 AGENT CAPABILITIES DEMO")
    print("="*60)
    
    # Initialize multi-agent manager
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        # Show available agents
        agents = manager.get_all_agents()
        print(f"\n🤖 Available Agents:")
        for agent in agents:
            print(f"   • {agent.name} ({agent.role.value})")
            print(f"     Capabilities: {[cap.value for cap in agent.capabilities]}")
            print(f"     Model: {agent.model_name}")
        
        # Test coordinator agent
        coordinator = manager.get_agent_by_role(AgentRole.COORDINATOR)
        if coordinator:
            print(f"\n🎯 Testing Coordinator Agent:")
            query = "I need help with a complex task that involves research and calculations"
            print(f"   Query: {query}")
            
            response = await coordinator.process_message(query)
            print(f"   Response: {response.content[:200]}...")
        
    finally:
        await manager.shutdown()


async def demo_error_handling():
    """Demo error handling in tool execution."""
    print("\n" + "="*60)
    print("⚠️  ERROR HANDLING DEMO")
    print("="*60)
    
    # Initialize multi-agent manager
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        # Test error handling with invalid tool
        query = "Execute a non-existent tool called 'magic_wand'"
        print(f"\n👤 User: {query}")
        print(f"\n🔍 This will demonstrate:")
        print(f"   • Tool availability checking")
        print(f"   • Error handling and reporting")
        print(f"   • Graceful failure recovery")
        
        response = await manager.process_query(query)
        print(f"\n🤖 Final Response: {response}")
        
    finally:
        await manager.shutdown()


async def demo_performance_monitoring():
    """Demo performance monitoring and statistics."""
    print("\n" + "="*60)
    print("📊 PERFORMANCE MONITORING DEMO")
    print("="*60)
    
    # Initialize multi-agent manager
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        # Run a few queries to generate statistics
        queries = [
            "Calculate 10 + 20",
            "What is 15 * 3?",
            "Search for Python programming tips"
        ]
        
        for query in queries:
            print(f"\n👤 User: {query}")
            response = await manager.process_query(query)
            print(f"🤖 Response: {response[:100]}...")
        
        # Show performance statistics
        tool_executor = manager.get_agent_by_role(AgentRole.TOOL_EXECUTOR)
        if tool_executor:
            stats = tool_executor.get_tool_stats()
            print(f"\n📊 Tool Execution Statistics:")
            for tool_name, tool_stats in stats.items():
                print(f"   🔧 {tool_name}:")
                print(f"      Total executions: {tool_stats['total_executions']}")
                print(f"      Successful: {tool_stats['successful_executions']}")
                print(f"      Failed: {tool_stats['failed_executions']}")
                print(f"      Avg time: {tool_stats['average_execution_time']:.2f}s")
        
    finally:
        await manager.shutdown()


async def main():
    """Run all demos."""
    print("🚀 PROJECT ZOHAR MULTI-AGENT FRAMEWORK DEMO")
    print("="*60)
    print("This demo showcases the multi-agent framework with detailed")
    print("logging of tool execution processes and model communication.")
    print("="*60)
    
    demos = [
        ("Basic Multi-Agent Interaction", demo_basic_multi_agent),
        ("Detailed Tool Execution Process", demo_tool_execution_process),
        ("Search and Synthesis", demo_search_and_synthesis),
        ("Code Execution", demo_code_execution),
        ("Weather Integration", demo_weather_integration),
        ("Complex Multi-Tool Task", demo_complex_multi_tool_task),
        ("Agent Capabilities", demo_agent_capabilities),
        ("Error Handling", demo_error_handling),
        ("Performance Monitoring", demo_performance_monitoring),
    ]
    
    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            print(f"\n🎬 Demo {i}/{len(demos)}: {name}")
            await demo_func()
            
            if i < len(demos):
                print(f"\n⏸️  Press Enter to continue to next demo...")
                input()
                
        except Exception as e:
            print(f"❌ Error in demo '{name}': {e}")
            logger.error(f"Demo error: {e}", exc_info=True)
    
    print(f"\n✅ All demos completed!")
    print(f"📋 Check the logs for detailed tool execution information.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logger.error(f"Demo failed: {e}", exc_info=True) 