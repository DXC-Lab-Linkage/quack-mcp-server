"""
Job management system for asynchronous processing.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Deque
from collections import deque

from .enums import JobType, JobStatus
from .base import Job, JobProcessor

logger = logging.getLogger("quack")


class JobManager:
    """
    Manages asynchronous jobs of any type
    
    The manager is responsible for:
    1. Creating jobs via the factory
    2. Starting background tasks for processing
    3. Tracking job status and history
    4. Providing access to job results
    """
    
    def __init__(self, max_history: int = 100):
        """
        Initialize a new job manager
        
        Args:
            max_history: Maximum number of completed jobs to keep in history
        """
        self.jobs: Dict[str, Job] = {}  # job_id -> Job
        self.job_history: Deque[Job] = deque(maxlen=max_history)  # Limited history of completed jobs
        self.active_tasks: Dict[str, asyncio.Task] = {}  # job_id -> asyncio.Task
    
    def submit_job(self, job_type: JobType, code: str) -> Job:
        """
        Submit a new job for processing
        
        Args:
            job_type: Type of job to create
            code: Python code to analyze
            
        Returns:
            The newly created job instance
            
        This method creates a job and starts processing it asynchronously.
        """
        # Import here to avoid circular imports
        from .factory import JobFactory
        
        # Create appropriate job type
        job = JobFactory.create_job(job_type, code)
        
        # Store job
        self.jobs[job.id] = job
        
        # Start background task
        processor = JobFactory.get_processor(job_type)
        task = asyncio.create_task(self._process_job(job, processor))
        self.active_tasks[job.id] = task
        
        return job
    
    async def _process_job(self, job: Job, processor: JobProcessor) -> None:
        """
        Process a job using the appropriate processor
        
        Args:
            job: The job to process
            processor: The processor to use
            
        This internal method handles job processing and cleanup.
        """
        try:
            await processor.process(job)
        finally:
            # Move to history if completed
            if job.status.is_terminal():
                self.job_history.append(job)
                # Clean up active tasks
                if job.id in self.active_tasks:
                    del self.active_tasks[job.id]
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a job by ID
        
        Args:
            job_id: ID of the job to retrieve
            
        Returns:
            The job if found, None otherwise
        """
        return self.jobs.get(job_id)
    
    def list_jobs(self, job_type: Optional[JobType] = None) -> List[Dict[str, Any]]:
        """
        List all jobs, optionally filtered by type
        
        Args:
            job_type: Optional filter for job type
            
        Returns:
            List of job dictionaries
        """
        jobs_info = []
        for job in self.jobs.values():
            if job_type is None or job.job_type == job_type:
                jobs_info.append(job.to_dict())
        return jobs_info
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about jobs
        
        Returns:
            Dictionary with job statistics
        """
        total = len(self.jobs)
        by_status = {}
        by_type = {}
        
        for job in self.jobs.values():
            # Count by status
            status_key = job.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1
            
            # Count by type
            type_key = job.job_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
        
        return {
            "total_jobs": total,
            "by_status": by_status,
            "by_type": by_type
        }
