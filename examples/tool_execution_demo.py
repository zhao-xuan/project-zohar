#!/usr/bin/env python3
"""
Tool Execution Process Demo for Project Zohar.

This script demonstrates the detailed process of tool execution,
including model communication, tool calling, and result synthesis.
"""

import asyncio
import logging
import sys
import json
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from zohar.core.multi_agent.multi_agent_manager import MultiAgentManager
from zohar.core.multi_agent.agent_types import AgentRole
from zohar.utils.logging import setup_logging

# Setup detailed logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_math_tool_execution():
    """Demonstrate detailed math tool execution process."""
    print("\n" + "="*80)
    print("🧮 MATH TOOL EXECUTION PROCESS DEMO")
    print("="*80)
    
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        query = "Calculate 25 * 17 + 8"
        print(f"\n👤 User Query: {query}")
        print(f"\n🔍 This will demonstrate the complete tool execution process:")
        print(f"   1. Task analysis and tool selection")
        print(f"   2. Parameter extraction from natural language")
        print(f"   3. Tool function retrieval and validation")
        print(f"   4. Tool execution with model communication")
        print(f"   5. Result processing and synthesis")
        print(f"   6. Response formatting and delivery")
        
        print(f"\n🚀 Starting tool execution process...")
        print(f"   " + "-"*60)
        
        response = await manager.process_query(query)
        
        print(f"\n✅ Tool execution completed!")
        print(f"🤖 Final Response: {response}")
        
        # Show detailed execution log
        tool_executor = manager.get_agent_by_role(AgentRole.TOOL_EXECUTOR)
        if tool_executor:
            execution_log = tool_executor.get_execution_log(limit=20)
            print(f"\n📋 Detailed Execution Log:")
            print(f"   " + "-"*60)
            for entry in execution_log:
                timestamp = entry['timestamp'].split('T')[1][:8]  # HH:MM:SS
                step = entry['step']
                data = entry['data']
                print(f"   [{timestamp}] {step}")
                if data:
                    print(f"       Data: {json.dumps(data, indent=6)}")
        
    finally:
        await manager.shutdown()


async def demo_search_tool_execution():
    """Demonstrate detailed search tool execution process."""
    print("\n" + "="*80)
    print("🔍 SEARCH TOOL EXECUTION PROCESS DEMO")
    print("="*80)
    
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        query = "Search for information about machine learning algorithms"
        print(f"\n👤 User Query: {query}")
        print(f"\n🔍 This will demonstrate:")
        print(f"   1. Search query extraction and validation")
        print(f"   2. Web search tool selection")
        print(f"   3. API call execution and response handling")
        print(f"   4. Result parsing and content extraction")
        print(f"   5. Information synthesis and summarization")
        
        print(f"\n🚀 Starting search tool execution...")
        print(f"   " + "-"*60)
        
        response = await manager.process_query(query)
        
        print(f"\n✅ Search execution completed!")
        print(f"🤖 Final Response: {response[:500]}...")
        
        # Show tool statistics
        tool_executor = manager.get_agent_by_role(AgentRole.TOOL_EXECUTOR)
        if tool_executor:
            stats = tool_executor.get_tool_stats()
            print(f"\n📊 Search Tool Statistics:")
            for tool_name, tool_stats in stats.items():
                if 'search' in tool_name.lower():
                    print(f"   🔧 {tool_name}:")
                    print(f"      Total executions: {tool_stats['total_executions']}")
                    print(f"      Successful: {tool_stats['successful_executions']}")
                    print(f"      Failed: {tool_stats['failed_executions']}")
                    print(f"      Avg time: {tool_stats['average_execution_time']:.2f}s")
        
    finally:
        await manager.shutdown()


async def demo_code_execution_process():
    """Demonstrate detailed code execution process."""
    print("\n" + "="*80)
    print("💻 CODE EXECUTION PROCESS DEMO")
    print("="*80)
    
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        query = "Write a Python function to calculate the sum of all even numbers in a list"
        print(f"\n👤 User Query: {query}")
        print(f"\n🔍 This will demonstrate:")
        print(f"   1. Code generation request analysis")
        print(f"   2. Code execution tool selection")
        print(f"   3. Python code generation and validation")
        print(f"   4. Code execution in safe environment")
        print(f"   5. Result capture and error handling")
        print(f"   6. Code output formatting and presentation")
        
        print(f"\n🚀 Starting code execution process...")
        print(f"   " + "-"*60)
        
        response = await manager.process_query(query)
        
        print(f"\n✅ Code execution completed!")
        print(f"🤖 Final Response: {response[:800]}...")
        
    finally:
        await manager.shutdown()


async def demo_multi_tool_coordination():
    """Demonstrate coordination between multiple tools."""
    print("\n" + "="*80)
    print("🎯 MULTI-TOOL COORDINATION DEMO")
    print("="*80)
    
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        query = "Search for the latest AI news and calculate how many days it's been since the first AI paper in 1956"
        print(f"\n👤 User Query: {query}")
        print(f"\n🔍 This will demonstrate:")
        print(f"   1. Multi-tool task decomposition")
        print(f"   2. Tool execution sequencing")
        print(f"   3. Result aggregation and synthesis")
        print(f"   4. Cross-tool data integration")
        print(f"   5. Final response composition")
        
        print(f"\n🚀 Starting multi-tool coordination...")
        print(f"   " + "-"*60)
        
        response = await manager.process_query(query)
        
        print(f"\n✅ Multi-tool coordination completed!")
        print(f"🤖 Final Response: {response[:600]}...")
        
        # Show coordination statistics
        tool_executor = manager.get_agent_by_role(AgentRole.TOOL_EXECUTOR)
        if tool_executor:
            stats = tool_executor.get_tool_stats()
            print(f"\n📊 Multi-Tool Execution Statistics:")
            for tool_name, tool_stats in stats.items():
                print(f"   🔧 {tool_name}:")
                print(f"      Executions: {tool_stats['total_executions']}")
                print(f"      Success rate: {tool_stats['successful_executions']}/{tool_stats['total_executions']}")
                print(f"      Avg time: {tool_stats['average_execution_time']:.2f}s")
        
    finally:
        await manager.shutdown()


async def demo_error_handling_process():
    """Demonstrate error handling in tool execution."""
    print("\n" + "="*80)
    print("⚠️  ERROR HANDLING PROCESS DEMO")
    print("="*80)
    
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        # Test various error scenarios
        error_scenarios = [
            "Execute a non-existent tool called 'magic_wand'",
            "Calculate with invalid parameters like 'abc' + 'def'",
            "Search for something that might cause API errors"
        ]
        
        for i, query in enumerate(error_scenarios, 1):
            print(f"\n🔍 Error Scenario {i}: {query}")
            print(f"   " + "-"*60)
            
            response = await manager.process_query(query)
            print(f"🤖 Error Response: {response}")
            
            if i < len(error_scenarios):
                print(f"\n⏸️  Press Enter to continue to next error scenario...")
                input()
        
        # Show error statistics
        tool_executor = manager.get_agent_by_role(AgentRole.TOOL_EXECUTOR)
        if tool_executor:
            stats = tool_executor.get_tool_stats()
            print(f"\n📊 Error Handling Statistics:")
            total_errors = sum(stats[tool]['failed_executions'] for tool in stats)
            total_executions = sum(stats[tool]['total_executions'] for tool in stats)
            error_rate = (total_errors / total_executions * 100) if total_executions > 0 else 0
            print(f"   Total executions: {total_executions}")
            print(f"   Total errors: {total_errors}")
            print(f"   Error rate: {error_rate:.1f}%")
        
    finally:
        await manager.shutdown()


async def demo_performance_analysis():
    """Demonstrate performance analysis of tool execution."""
    print("\n" + "="*80)
    print("📊 PERFORMANCE ANALYSIS DEMO")
    print("="*80)
    
    manager = MultiAgentManager()
    await manager.initialize()
    
    try:
        # Run a series of queries to generate performance data
        performance_queries = [
            "Calculate 10 + 20",
            "What is 15 * 3?",
            "Search for Python programming tips",
            "Write a simple hello world function",
            "Calculate the factorial of 5"
        ]
        
        print(f"\n🚀 Running performance test queries...")
        print(f"   " + "-"*60)
        
        import time
        total_start_time = time.time()
        
        for i, query in enumerate(performance_queries, 1):
            print(f"\n🔍 Query {i}: {query}")
            start_time = time.time()
            
            response = await manager.process_query(query)
            
            query_time = time.time() - start_time
            print(f"   ⏱️  Query time: {query_time:.2f}s")
            print(f"   🤖 Response: {response[:100]}...")
        
        total_time = time.time() - total_start_time
        avg_time = total_time / len(performance_queries)
        
        print(f"\n📈 Performance Summary:")
        print(f"   Total queries: {len(performance_queries)}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Average time per query: {avg_time:.2f}s")
        print(f"   Queries per second: {len(performance_queries) / total_time:.2f}")
        
        # Show detailed tool performance
        tool_executor = manager.get_agent_by_role(AgentRole.TOOL_EXECUTOR)
        if tool_executor:
            stats = tool_executor.get_tool_stats()
            print(f"\n🔧 Tool Performance Breakdown:")
            for tool_name, tool_stats in stats.items():
                if tool_stats['total_executions'] > 0:
                    success_rate = (tool_stats['successful_executions'] / tool_stats['total_executions']) * 100
                    print(f"   {tool_name}:")
                    print(f"      Executions: {tool_stats['total_executions']}")
                    print(f"      Success rate: {success_rate:.1f}%")
                    print(f"      Avg time: {tool_stats['average_execution_time']:.2f}s")
                    print(f"      Total time: {tool_stats['total_execution_time']:.2f}s")
        
    finally:
        await manager.shutdown()


async def main():
    """Run all tool execution demos."""
    print("🚀 PROJECT ZOHAR TOOL EXECUTION PROCESS DEMO")
    print("="*80)
    print("This demo showcases the detailed process of tool execution")
    print("including model communication, tool calling, and result synthesis.")
    print("="*80)
    
    demos = [
        ("Math Tool Execution", demo_math_tool_execution),
        ("Search Tool Execution", demo_search_tool_execution),
        ("Code Execution Process", demo_code_execution_process),
        ("Multi-Tool Coordination", demo_multi_tool_coordination),
        ("Error Handling Process", demo_error_handling_process),
        ("Performance Analysis", demo_performance_analysis),
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
    
    print(f"\n✅ All tool execution demos completed!")
    print(f"📋 Check the logs for detailed tool execution information.")
    print(f"🔍 The logs show the complete process of:")
    print(f"   • Model communication and tool calling")
    print(f"   • Parameter extraction and validation")
    print(f"   • Tool execution and result handling")
    print(f"   • Error handling and recovery")
    print(f"   • Performance monitoring and optimization")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logger.error(f"Demo failed: {e}", exc_info=True) 