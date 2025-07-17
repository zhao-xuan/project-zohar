#!/usr/bin/env python3
"""
Standalone Chat History CLI

A standalone version of the chat history CLI that can be run independently
without complex dependencies.
"""

import argparse
import json
import sys
from pathlib import Path
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the simple analyzer
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'examples'))
from simple_chat_analyzer import SimpleChatAnalyzer, create_sample_data


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Simple Chat History Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze Slack export
  python standalone_cli.py analyze --slack-export ./slack_export

  # Create sample data and analyze
  python standalone_cli.py demo

  # Search messages
  python standalone_cli.py search --query "project"

  # Show analytics
  python standalone_cli.py analytics
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Demo command
    demo_parser = subparsers.add_parser('demo', help='Run demo with sample data')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze chat history')
    analyze_parser.add_argument('--slack-export', type=str, required=True, help='Path to Slack export directory')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search messages')
    search_parser.add_argument('--query', type=str, required=True, help='Search query')
    search_parser.add_argument('--db', type=str, default='./data/simple_chat.db', help='Database path')
    
    # Analytics command
    analytics_parser = subparsers.add_parser('analytics', help='Show analytics')
    analytics_parser.add_argument('--db', type=str, default='./data/simple_chat.db', help='Database path')
    
    args = parser.parse_args()
    
    if args.command == 'demo':
        handle_demo()
    elif args.command == 'analyze':
        handle_analyze(args)
    elif args.command == 'search':
        handle_search(args)
    elif args.command == 'analytics':
        handle_analytics(args)
    else:
        parser.print_help()


def handle_demo():
    """Handle demo command"""
    print("🚀 Chat History Analysis Demo")
    print("=" * 40)
    
    # Create sample data
    sample_export = create_sample_data()
    
    # Initialize analyzer
    analyzer = SimpleChatAnalyzer("./data/demo_chat.db")
    
    # Process sample data
    print("\n📊 Processing sample data...")
    analyzer.analyze_slack_export(sample_export)
    
    # Show analytics
    print("\n📈 Analytics:")
    show_analytics(analyzer)
    
    # Show search example
    print("\n🔍 Search example (query: 'project'):")
    results = analyzer.search_messages("project")
    for platform, channel, sender, content, timestamp in results:
        print(f"  [{platform}] #{channel} - {sender}: {content[:80]}...")
    
    print("\n✅ Demo complete!")


def handle_analyze(args):
    """Handle analyze command"""
    print(f"📊 Analyzing Slack export: {args.slack_export}")
    
    if not Path(args.slack_export).exists():
        print(f"❌ Export path not found: {args.slack_export}")
        return
    
    analyzer = SimpleChatAnalyzer("./data/simple_chat.db")
    count = analyzer.analyze_slack_export(args.slack_export)
    
    print(f"✅ Processed {count} messages")
    show_analytics(analyzer)


def handle_search(args):
    """Handle search command"""
    print(f"🔍 Searching for: '{args.query}'")
    
    if not Path(args.db).exists():
        print(f"❌ Database not found: {args.db}")
        print("Run 'analyze' command first to create the database")
        return
    
    analyzer = SimpleChatAnalyzer(args.db)
    results = analyzer.search_messages(args.query)
    
    print(f"📄 Found {len(results)} results:")
    for platform, channel, sender, content, timestamp in results:
        print(f"  [{platform}] #{channel} - {sender}: {content[:100]}...")


def handle_analytics(args):
    """Handle analytics command"""
    print("📈 Chat Analytics")
    
    if not Path(args.db).exists():
        print(f"❌ Database not found: {args.db}")
        print("Run 'analyze' command first to create the database")
        return
    
    analyzer = SimpleChatAnalyzer(args.db)
    show_analytics(analyzer)


def show_analytics(analyzer):
    """Show analytics from analyzer"""
    analytics = analyzer.get_analytics()
    
    print(f"📊 Total messages: {analytics['total_messages']}")
    print(f"🏷️  Entity counts: {analytics['entity_counts']}")
    
    print("\n👥 Top senders:")
    for sender, count in analytics['top_senders'][:5]:
        print(f"  {sender}: {count} messages")
    
    print("\n💬 Top channels:")
    for channel, count in analytics['top_channels'][:5]:
        print(f"  #{channel}: {count} messages")
    
    print("\n🔥 Top entities:")
    for entity, count in analytics['top_entities'][:5]:
        print(f"  {entity}: {count} mentions")


if __name__ == "__main__":
    main()
