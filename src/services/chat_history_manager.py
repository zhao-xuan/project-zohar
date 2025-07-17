#!/usr/bin/env python3
"""
Chat History Integration Module

This module provides a high-level interface for integrating the chat history parser
with the existing project structure and provides easy-to-use functions for various
chat analysis tasks.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

# Import chat history modules
from .chat_history_parser import (
    ChatHistoryProcessor, 
    ChatPlatform, 
    SlackConnector, 
    TeamsConnector,
    create_chat_processor,
    create_slack_connector,
    create_teams_connector
)
from .chat_history_scheduler import ChatHistoryScheduler, ScheduleInterval, create_default_scheduler
from .chat_history_config import ChatHistoryConfig, load_config_from_file, load_config_from_env, create_default_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatHistoryManager:
    """Main manager class for chat history analysis"""
    
    def __init__(self, config: ChatHistoryConfig = None):
        self.config = config or create_default_config()
        self.processor = None
        self.scheduler = None
        self.setup_complete = False
        
    async def setup(self):
        """Initialize all components"""
        logger.info("Setting up Chat History Manager...")
        
        # Create processor with config
        processor_config = {
            'knowledge_graph_db': self.config.database.knowledge_graph_db,
            'vector_store_db': self.config.database.vector_store_db,
            'embedding_model': self.config.embedding.model_name
        }
        
        self.processor = create_chat_processor(processor_config)
        
        # Setup platform connectors
        await self._setup_connectors()
        
        # Setup scheduler if enabled
        if self.config.scheduling.enable_scheduling:
            await self._setup_scheduler()
        
        # Ensure data directories exist
        self._ensure_directories()
        
        self.setup_complete = True
        logger.info("Chat History Manager setup complete")
    
    async def _setup_connectors(self):
        """Setup platform connectors based on configuration"""
        
        # Setup Slack connector
        if self.config.slack.export_path or self.config.slack.api_token:
            slack_connector = create_slack_connector(
                export_path=self.config.slack.export_path,
                api_token=self.config.slack.api_token
            )
            self.processor.register_connector(ChatPlatform.SLACK, slack_connector)
            logger.info("Slack connector registered")
        
        # Setup Teams connector
        if self.config.teams.client_id and self.config.teams.client_secret:
            teams_connector = create_teams_connector(
                client_id=self.config.teams.client_id,
                client_secret=self.config.teams.client_secret
            )
            self.processor.register_connector(ChatPlatform.TEAMS, teams_connector)
            logger.info("Teams connector registered")
        
        # TODO: Add other platform connectors as needed
    
    async def _setup_scheduler(self):
        """Setup the autonomous scheduler"""
        self.scheduler = ChatHistoryScheduler({
            'state_file': './data/scheduler_state.json'
        })
        
        # Register scheduled jobs based on configuration
        if self.config.scheduling.schedule_interval == "daily":
            interval = ScheduleInterval.DAILY
        elif self.config.scheduling.schedule_interval == "weekly":
            interval = ScheduleInterval.WEEKLY
        elif self.config.scheduling.schedule_interval == "monthly":
            interval = ScheduleInterval.MONTHLY
        else:
            interval = ScheduleInterval.WEEKLY
        
        # Add main analysis job
        self.scheduler.add_job(
            job_id="main_analysis",
            name="Main Chat Analysis",
            interval=interval,
            time=self.config.scheduling.schedule_time,
            callback=self._scheduled_analysis_callback,
            metadata={
                "lookback_days": self.config.scheduling.lookback_days,
                "max_retries": self.config.scheduling.max_retries
            }
        )
        
        logger.info(f"Scheduler setup with {interval.value} interval at {self.config.scheduling.schedule_time}")
    
    def _ensure_directories(self):
        """Ensure all necessary directories exist"""
        dirs_to_create = [
            Path(self.config.database.knowledge_graph_db).parent,
            Path(self.config.database.vector_store_db),
            Path(self.config.database.backup_path),
            Path("./data/logs"),
            Path("./data/exports")
        ]
        
        for directory in dirs_to_create:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def _scheduled_analysis_callback(self, job):
        """Callback for scheduled analysis jobs"""
        logger.info(f"Running scheduled analysis: {job.name}")
        
        try:
            lookback_days = job.metadata.get('lookback_days', 7)
            end_time = datetime.now()
            start_time = end_time - timedelta(days=lookback_days)
            
            results = await self.processor.run_analysis_cycle(start_time, end_time)
            
            # Save results to file
            results_file = Path(f"./data/exports/analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Scheduled analysis completed. Results saved to {results_file}")
            
        except Exception as e:
            logger.error(f"Error in scheduled analysis: {e}")
    
    async def analyze_period(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Analyze chat history for a specific time period"""
        if not self.setup_complete:
            await self.setup()
        
        return await self.processor.run_analysis_cycle(start_time, end_time)
    
    async def analyze_last_days(self, days: int = 7) -> Dict[str, Any]:
        """Analyze chat history for the last N days"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        return await self.analyze_period(start_time, end_time)
    
    async def analyze_last_week(self) -> Dict[str, Any]:
        """Analyze chat history for the last week"""
        return await self.analyze_last_days(7)
    
    async def analyze_last_month(self) -> Dict[str, Any]:
        """Analyze chat history for the last month"""
        return await self.analyze_last_days(30)
    
    def get_analytics_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get analytics summary for the last N days"""
        if not self.setup_complete:
            raise RuntimeError("Manager not setup. Call setup() first.")
        
        return self.processor.get_analytics_summary(days)
    
    def search_messages(self, query: str, platform: Optional[ChatPlatform] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search messages using semantic search"""
        if not self.setup_complete:
            raise RuntimeError("Manager not setup. Call setup() first.")
        
        results = self.processor.vector_store.search_similar_messages(query, limit, platform)
        return results
    
    def get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get relationships for a specific entity"""
        if not self.setup_complete:
            raise RuntimeError("Manager not setup. Call setup() first.")
        
        return self.processor.knowledge_graph.get_entity_relationships(entity_id)
    
    def find_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """Find entities by type (person, topic, project, channel)"""
        if not self.setup_complete:
            raise RuntimeError("Manager not setup. Call setup() first.")
        
        return self.processor.knowledge_graph.find_entities_by_type(entity_type)
    
    async def start_scheduler(self):
        """Start the autonomous scheduler"""
        if not self.scheduler:
            raise RuntimeError("Scheduler not configured. Enable scheduling in config.")
        
        await self.scheduler.run_scheduler()
    
    def stop_scheduler(self):
        """Stop the autonomous scheduler"""
        if self.scheduler:
            self.scheduler.stop_scheduler()
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        if not self.scheduler:
            return {"scheduler_enabled": False}
        
        return self.scheduler.get_job_status()
    
    def export_knowledge_graph(self, output_path: str) -> bool:
        """Export knowledge graph to JSON file"""
        try:
            if not self.setup_complete:
                raise RuntimeError("Manager not setup. Call setup() first.")
            
            # Get all entities and relationships
            entities = {}
            relationships = []
            
            for entity_type in ['person', 'topic', 'project', 'channel']:
                entities[entity_type] = self.find_entities_by_type(entity_type)
            
            # Get relationships for all entities
            for entity_type, entity_list in entities.items():
                for entity in entity_list:
                    entity_relationships = self.get_entity_relationships(entity['entity_id'])
                    relationships.extend(entity_relationships)
            
            # Remove duplicates
            unique_relationships = []
            seen = set()
            for rel in relationships:
                rel_key = (rel['source_entity'], rel['target_entity'], rel['relationship_type'])
                if rel_key not in seen:
                    seen.add(rel_key)
                    unique_relationships.append(rel)
            
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'entities': entities,
                'relationships': unique_relationships,
                'total_entities': sum(len(entity_list) for entity_list in entities.values()),
                'total_relationships': len(unique_relationships)
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Knowledge graph exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting knowledge graph: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        status = {
            'setup_complete': self.setup_complete,
            'config_loaded': self.config is not None,
            'processor_ready': self.processor is not None,
            'scheduler_enabled': self.scheduler is not None,
            'registered_platforms': [],
            'database_paths': {
                'knowledge_graph': self.config.database.knowledge_graph_db,
                'vector_store': self.config.database.vector_store_db
            }
        }
        
        if self.processor:
            status['registered_platforms'] = [platform.value for platform in self.processor.connectors.keys()]
        
        if self.scheduler:
            status['scheduler_status'] = self.get_scheduler_status()
        
        return status


# Convenience functions for easy integration
def create_chat_history_manager(config_path: str = None) -> ChatHistoryManager:
    """Create a chat history manager with configuration"""
    if config_path:
        config = load_config_from_file(config_path)
    else:
        config = load_config_from_env()
    
    return ChatHistoryManager(config)


async def quick_analysis(days: int = 7, slack_export_path: str = None) -> Dict[str, Any]:
    """Quick analysis function for immediate use"""
    config = create_default_config()
    
    if slack_export_path:
        config.slack.export_path = slack_export_path
    
    manager = ChatHistoryManager(config)
    await manager.setup()
    
    return await manager.analyze_last_days(days)


async def analyze_slack_export(export_path: str, days: int = 30) -> Dict[str, Any]:
    """Analyze Slack export data"""
    config = create_default_config()
    config.slack.export_path = export_path
    
    manager = ChatHistoryManager(config)
    await manager.setup()
    
    return await manager.analyze_last_days(days)


# Example usage and CLI interface
async def main():
    """Example usage of the chat history manager"""
    # Create manager with default config
    manager = ChatHistoryManager()
    
    # Setup the manager
    await manager.setup()
    
    # Get system status
    status = manager.get_system_status()
    print(f"System status: {json.dumps(status, indent=2)}")
    
    # If no platforms are configured, show example
    if not status['registered_platforms']:
        print("No platforms configured. To use the system:")
        print("1. Set SLACK_EXPORT_PATH environment variable to your Slack export directory")
        print("2. Or configure other platforms in chat_history_config.py")
        print("3. Then run the analysis")
        return
    
    # Run a quick analysis
    print("\nRunning analysis for last 7 days...")
    try:
        results = await manager.analyze_last_week()
        print(f"Analysis results: {json.dumps(results, indent=2, default=str)}")
        
        # Get analytics summary
        analytics = manager.get_analytics_summary(7)
        print(f"Analytics summary: {json.dumps(analytics, indent=2)}")
        
        # Export knowledge graph
        export_path = "./data/exports/knowledge_graph_export.json"
        if manager.export_knowledge_graph(export_path):
            print(f"Knowledge graph exported to {export_path}")
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}")


if __name__ == "__main__":
    asyncio.run(main())
