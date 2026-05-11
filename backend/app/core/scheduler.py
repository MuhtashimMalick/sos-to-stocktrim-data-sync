import logging
from typing import Callable, Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Registry to store all scheduled job definitions
# Format: {"job_id": {"func": callable, "minutes": int, "name": str}}
_job_registry: Dict[str, Dict] = {}


def register_job(job_id: str, func: Callable, minutes: int, name: str) -> None:
    """
    Register a job to be scheduled.
    
    Args:
        job_id: Unique identifier for the job
        func: Async function to execute
        minutes: Interval in minutes between executions
        name: Human-readable name for the job
    """
    _job_registry[job_id] = {
        "func": func,
        "minutes": minutes,
        "name": name
    }
    logger.info(f"Registered job: {name} (ID: {job_id}, Interval: {minutes}min)")


async def start_scheduler() -> None:
    """Start the APScheduler and add all registered jobs."""
    try:
        if scheduler.running:
            logger.info("Scheduler is already running")
            return
        
        # Add all registered jobs to the scheduler
        for job_id, job_config in _job_registry.items():
            scheduler.add_job(
                job_config["func"],
                trigger=IntervalTrigger(minutes=job_config["minutes"]),
                id=job_id,
                name=job_config["name"],
                replace_existing=True
            )
            logger.info(f"Added job to scheduler: {job_config['name']}")
        
        scheduler.start()
        logger.info("Scheduler started successfully")
        
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")
        raise


async def shutdown_scheduler() -> None:
    """Shutdown the APScheduler gracefully."""
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Scheduler shutdown successfully")
            
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {str(e)}")


def get_scheduler():
    """Get the scheduler instance."""
    return scheduler
