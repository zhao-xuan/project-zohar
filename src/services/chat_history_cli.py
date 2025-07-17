#!/usr/bin/env python3
"""
Chat History CLI Interface

Command-line interface for the chat history parser module.
Provides easy access to analysis functions and configuration management.
"""

import asyncio
import argparse
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.chat_history_manager import ChatHistoryManager, create_chat_history_manager, analyze_slack_export
from services.chat_history_config import create_default_config, save_config_to_file, load_config_from_file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_argument_parser():
    """Setup command-line argument parser"""
    parser = argparse.ArgumentParser(
        description="Chat History Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze Slack export for last 7 days
  python chat_history_cli.py analyze --slack-export ./slack_export --days 7

  # Run scheduled analysis
  python chat_history_cli.py schedule --start

  # Search messages
  python chat_history_cli.py search --query "project update"

  # Export knowledge graph
  python chat_history_cli.py export --output ./knowledge_graph.json

  # Show system status
  python chat_history_cli.py status
        """
    )
    
    # Global options
    parser.add_argument('--config', '-c', type=str, help='Path to configuration file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode (errors only)')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze chat history')
    analyze_parser.add_argument('--days', '-d', type=int, default=7, help='Number of days to analyze')
    analyze_parser.add_argument('--slack-export', type=str, help='Path to Slack export directory')
    analyze_parser.add_argument('--output', '-o', type=str, help='Output file for results')
    analyze_parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    analyze_parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    
    # Schedule command
    schedule_parser = subparsers.add_parser('schedule', help='Manage scheduled analysis')
    schedule_parser.add_argument('--start', action='store_true', help='Start the scheduler')
    schedule_parser.add_argument('--stop', action='store_true', help='Stop the scheduler')
    schedule_parser.add_argument('--status', action='store_true', help='Show scheduler status')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search messages')
    search_parser.add_argument('--query', '-q', type=str, required=True, help='Search query')
    search_parser.add_argument('--platform', type=str, help='Platform to search (slack, teams, etc.)')
    search_parser.add_argument('--limit', '-l', type=int, default=10, help='Maximum results')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export data')
    export_parser.add_argument('--output', '-o', type=str, required=True, help='Output file path')
    export_parser.add_argument('--format', type=str, choices=['json', 'csv'], default='json', help='Output format')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Manage configuration')
    config_parser.add_argument('--create', action='store_true', help='Create default configuration')
    config_parser.add_argument('--show', action='store_true', help='Show current configuration')
    config_parser.add_argument('--output', '-o', type=str, help='Output file for configuration')
    
    return parser


async def handle_analyze_command(args):
    """Handle the analyze command"""
    print("🔍 Starting chat history analysis...")
    
    # Create manager
    if args.config:
        manager = create_chat_history_manager(args.config)
    else:
        manager = ChatHistoryManager()
    
    # Configure Slack export if provided
    if args.slack_export:
        manager.config.slack.export_path = args.slack_export
        print(f"📂 Using Slack export: {args.slack_export}")
    
    # Setup manager
    await manager.setup()
    
    # Determine time range
    if args.start_date and args.end_date:
        start_time = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_time = datetime.strptime(args.end_date, '%Y-%m-%d')
        results = await manager.analyze_period(start_time, end_time)
        print(f"📊 Analyzed period: {args.start_date} to {args.end_date}")
    else:
        results = await manager.analyze_last_days(args.days)
        print(f"📊 Analyzed last {args.days} days")
    
    # Display results
    print(f"✅ Analysis complete!")
    print(f"   Total messages: {results['total_messages']}")
    print(f"   Total entities: {results['total_entities']}")
    print(f"   Total relationships: {results['total_relationships']}")
    
    # Show platform breakdown
    print("\n📱 Platform breakdown:")
    for platform, data in results['platforms'].items():
        if 'error' in data:
            print(f"   {platform}: ❌ {data['error']}")
        else:
            print(f"   {platform}: {data['messages']} messages, {data['entities']} entities")
    
    # Save results if output specified
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"💾 Results saved to {args.output}")
    
    # Get analytics summary
    analytics = manager.get_analytics_summary(args.days)
    print(f"\n📈 Analytics summary:")
    print(f"   Entity counts: {analytics['entity_counts']}")


async def handle_schedule_command(args):
    """Handle the schedule command"""
    manager = ChatHistoryManager()
    await manager.setup()
    
    if args.start:
        print("🕐 Starting scheduler...")
        try:
            await manager.start_scheduler()
        except KeyboardInterrupt:
            print("\n🛑 Scheduler stopped by user")
            manager.stop_scheduler()
    
    elif args.stop:
        print("🛑 Stopping scheduler...")
        manager.stop_scheduler()
    
    elif args.status:
        status = manager.get_scheduler_status()
        print("🕐 Scheduler status:")
        print(json.dumps(status, indent=2, default=str))


async def handle_search_command(args):
    """Handle the search command"""
    manager = ChatHistoryManager()
    await manager.setup()
    
    print(f"🔍 Searching for: '{args.query}'")
    
    platform = None
    if args.platform:
        from services.chat_history_parser import ChatPlatform
        platform = ChatPlatform(args.platform.lower())
    
    results = manager.search_messages(args.query, platform, args.limit)
    
    print(f"✅ Found {len(results.get('documents', []))} results:")
    
    for i, (doc, metadata) in enumerate(zip(results.get('documents', []), results.get('metadatas', []))):
        print(f"\n📄 Result {i+1}:")
        print(f"   Platform: {metadata.get('platform', 'unknown')}")
        print(f"   Channel: {metadata.get('channel_name', 'unknown')}")
        print(f"   Sender: {metadata.get('sender_name', 'unknown')}")
        print(f"   Time: {metadata.get('timestamp', 'unknown')}")
        print(f"   Content: {doc[:200]}{'...' if len(doc) > 200 else ''}")


async def handle_export_command(args):
    """Handle the export command"""
    manager = ChatHistoryManager()
    await manager.setup()
    
    print(f"📤 Exporting knowledge graph to {args.output}")
    
    if manager.export_knowledge_graph(args.output):
        print("✅ Export completed successfully")
    else:
        print("❌ Export failed")


async def handle_status_command(args):
    """Handle the status command"""
    manager = ChatHistoryManager()
    await manager.setup()
    
    status = manager.get_system_status()
    
    print("🖥️  System Status:")
    print(f"   Setup complete: {'✅' if status['setup_complete'] else '❌'}")
    print(f"   Config loaded: {'✅' if status['config_loaded'] else '❌'}")
    print(f"   Processor ready: {'✅' if status['processor_ready'] else '❌'}")
    print(f"   Scheduler enabled: {'✅' if status['scheduler_enabled'] else '❌'}")
    
    print(f"\n📱 Registered platforms: {', '.join(status['registered_platforms']) if status['registered_platforms'] else 'None'}")
    
    print(f"\n💾 Database paths:")
    print(f"   Knowledge graph: {status['database_paths']['knowledge_graph']}")
    print(f"   Vector store: {status['database_paths']['vector_store']}")
    
    if 'scheduler_status' in status:
        print(f"\n🕐 Scheduler: {status['scheduler_status']['total_jobs']} jobs")


def handle_config_command(args):
    """Handle the config command"""
    if args.create:
        config = create_default_config()
        output_path = args.output or './config/chat_history_config.json'
        save_config_to_file(config, output_path)
        print(f"📝 Default configuration created at {output_path}")
    
    elif args.show:
        if args.config:
            config = load_config_from_file(args.config)
        else:
            config = create_default_config()
        
        print("⚙️  Current configuration:")
        print(json.dumps(config.dict(), indent=2, default=str))


async def main():
    """Main CLI entry point"""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    
    # Handle commands
    try:
        if args.command == 'analyze':
            await handle_analyze_command(args)
        elif args.command == 'schedule':
            await handle_schedule_command(args)
        elif args.command == 'search':
            await handle_search_command(args)
        elif args.command == 'export':
            await handle_export_command(args)
        elif args.command == 'status':
            await handle_status_command(args)
        elif args.command == 'config':
            handle_config_command(args)
        else:
            parser.print_help()
    
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
