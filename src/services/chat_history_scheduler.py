#!/usr/bin/env python3
"""
Chat History Scheduler Module

This module provides scheduling functionality for autonomous chat history processing
as described in the multi-agent chat analysis system design.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScheduleInterval(Enum):
    """Supported scheduling intervals"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class ScheduledJob:
    """Represents a scheduled job"""
    job_id: str
    name: str
    interval: ScheduleInterval
    time: str  # HH:MM format
    last_run: Optional[datetime]
    next_run: datetime
    enabled: bool
    callback: Optional[Callable] = None
    metadata: Dict[str, Any] = None


class ChatHistoryScheduler:
    """Autonomous scheduler for chat history processing"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.jobs: Dict[str, ScheduledJob] = {}
        self.running = False
        self.state_file = self.config.get('state_file', './data/scheduler_state.json')
        self.load_state()
    
    def add_job(self, job_id: str, name: str, interval: ScheduleInterval, time: str, callback: Callable, metadata: Dict[str, Any] = None):
        """Add a scheduled job"""
        next_run = self._calculate_next_run(interval, time)
        
        job = ScheduledJob(
            job_id=job_id,
            name=name,
            interval=interval,
            time=time,
            last_run=None,
            next_run=next_run,
            enabled=True,
            callback=callback,
            metadata=metadata or {}
        )
        
        self.jobs[job_id] = job
        logger.info(f"Added job '{name}' ({job_id}) - next run: {next_run}")
        self.save_state()
    
    def remove_job(self, job_id: str):
        """Remove a scheduled job"""
        if job_id in self.jobs:
            job_name = self.jobs[job_id].name
            del self.jobs[job_id]
            logger.info(f"Removed job '{job_name}' ({job_id})")
            self.save_state()
    
    def enable_job(self, job_id: str):
        """Enable a scheduled job"""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = True
            logger.info(f"Enabled job {job_id}")
            self.save_state()
    
    def disable_job(self, job_id: str):
        """Disable a scheduled job"""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = False
            logger.info(f"Disabled job {job_id}")
            self.save_state()
    
    def _calculate_next_run(self, interval: ScheduleInterval, time: str) -> datetime:
        """Calculate the next run time for a job"""
        now = datetime.now()
        hour, minute = map(int, time.split(':'))
        
        if interval == ScheduleInterval.DAILY:
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        
        elif interval == ScheduleInterval.WEEKLY:
            # Schedule for next Monday at specified time
            days_ahead = 0 - now.weekday()  # Monday is 0
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
        
        elif interval == ScheduleInterval.MONTHLY:
            # Schedule for first day of next month at specified time
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1, hour=hour, minute=minute, second=0, microsecond=0)
            else:
                next_run = now.replace(month=now.month + 1, day=1, hour=hour, minute=minute, second=0, microsecond=0)
        
        return next_run
    
    def _update_next_run(self, job: ScheduledJob):
        """Update the next run time for a job after execution"""
        job.last_run = datetime.now()
        job.next_run = self._calculate_next_run(job.interval, job.time)
        logger.info(f"Updated next run for job {job.name}: {job.next_run}")
    
    async def run_scheduler(self):
        """Main scheduler loop"""
        logger.info("Starting chat history scheduler...")
        self.running = True
        
        while self.running:
            try:
                now = datetime.now()
                
                # Check for jobs that need to run
                for job_id, job in self.jobs.items():
                    if job.enabled and job.next_run <= now:
                        await self._execute_job(job)
                        self._update_next_run(job)
                        self.save_state()
                
                # Sleep for 60 seconds before checking again
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)
    
    async def _execute_job(self, job: ScheduledJob):
        """Execute a scheduled job"""
        logger.info(f"Executing job: {job.name} ({job.job_id})")
        
        try:
            if job.callback:
                # If callback is async
                if asyncio.iscoroutinefunction(job.callback):
                    await job.callback(job)
                else:
                    job.callback(job)
            else:
                logger.warning(f"No callback defined for job {job.name}")
                
        except Exception as e:
            logger.error(f"Error executing job {job.name}: {e}")
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        logger.info("Stopping chat history scheduler...")
        self.running = False
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get status of all scheduled jobs"""
        now = datetime.now()
        status = {
            'scheduler_running': self.running,
            'total_jobs': len(self.jobs),
            'enabled_jobs': sum(1 for job in self.jobs.values() if job.enabled),
            'jobs': []
        }
        
        for job_id, job in self.jobs.items():
            job_status = {
                'job_id': job_id,
                'name': job.name,
                'interval': job.interval.value,
                'time': job.time,
                'enabled': job.enabled,
                'last_run': job.last_run.isoformat() if job.last_run else None,
                'next_run': job.next_run.isoformat(),
                'time_until_next_run': str(job.next_run - now) if job.next_run > now else "Overdue"
            }
            status['jobs'].append(job_status)
        
        return status
    
    def save_state(self):
        """Save scheduler state to file"""
        try:
            state_data = {
                'jobs': {}
            }
            
            for job_id, job in self.jobs.items():
                state_data['jobs'][job_id] = {
                    'name': job.name,
                    'interval': job.interval.value,
                    'time': job.time,
                    'last_run': job.last_run.isoformat() if job.last_run else None,
                    'next_run': job.next_run.isoformat(),
                    'enabled': job.enabled,
                    'metadata': job.metadata
                }
            
            # Ensure directory exists
            state_file = Path(self.state_file)
            state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving scheduler state: {e}")
    
    def load_state(self):
        """Load scheduler state from file"""
        try:
            state_file = Path(self.state_file)
            if not state_file.exists():
                return
            
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            for job_id, job_data in state_data.get('jobs', {}).items():
                job = ScheduledJob(
                    job_id=job_id,
                    name=job_data['name'],
                    interval=ScheduleInterval(job_data['interval']),
                    time=job_data['time'],
                    last_run=datetime.fromisoformat(job_data['last_run']) if job_data['last_run'] else None,
                    next_run=datetime.fromisoformat(job_data['next_run']),
                    enabled=job_data['enabled'],
                    callback=None,  # Callbacks need to be re-registered
                    metadata=job_data.get('metadata', {})
                )
                self.jobs[job_id] = job
            
            logger.info(f"Loaded {len(self.jobs)} scheduled jobs from state file")
            
        except Exception as e:
            logger.error(f"Error loading scheduler state: {e}")


# Example callback functions for chat history processing
async def weekly_chat_analysis_job(job: ScheduledJob):
    """Example callback for weekly chat analysis"""
    logger.info(f"Running weekly chat analysis job: {job.name}")
    
    # This would typically call the ChatHistoryProcessor
    # processor = ChatHistoryProcessor()
    # end_time = datetime.now()
    # start_time = end_time - timedelta(days=7)
    # results = await processor.run_analysis_cycle(start_time, end_time)
    
    # For now, just log the execution
    logger.info(f"Weekly analysis completed for job {job.name}")


async def monthly_summary_job(job: ScheduledJob):
    """Example callback for monthly summary generation"""
    logger.info(f"Running monthly summary job: {job.name}")
    
    # This would typically generate a monthly summary
    # processor = ChatHistoryProcessor()
    # analytics = processor.get_analytics_summary(days=30)
    
    logger.info(f"Monthly summary completed for job {job.name}")


def create_default_scheduler() -> ChatHistoryScheduler:
    """Create a scheduler with default jobs"""
    scheduler = ChatHistoryScheduler()
    
    # Add default weekly analysis job
    scheduler.add_job(
        job_id="weekly_analysis",
        name="Weekly Chat Analysis",
        interval=ScheduleInterval.WEEKLY,
        time="02:00",
        callback=weekly_chat_analysis_job,
        metadata={"lookback_days": 7}
    )
    
    # Add default monthly summary job
    scheduler.add_job(
        job_id="monthly_summary",
        name="Monthly Chat Summary",
        interval=ScheduleInterval.MONTHLY,
        time="01:00",
        callback=monthly_summary_job,
        metadata={"lookback_days": 30}
    )
    
    return scheduler


# Example usage
async def main():
    """Example usage of the scheduler"""
    scheduler = create_default_scheduler()
    
    # Print current job status
    status = scheduler.get_job_status()
    print(f"Scheduler status: {json.dumps(status, indent=2)}")
    
    # Run scheduler for a short time (in production, this would run continuously)
    try:
        await asyncio.wait_for(scheduler.run_scheduler(), timeout=10)
    except asyncio.TimeoutError:
        scheduler.stop_scheduler()
        print("Scheduler stopped after timeout")


if __name__ == "__main__":
    asyncio.run(main())
