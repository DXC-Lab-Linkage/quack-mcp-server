"""
Base classes for jobs and processors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, TypeVar

from .enums import JobType, JobStatus


@dataclass
class Job(ABC):
    """Base class for all asynchronous jobs"""
    id: str
    status: JobStatus
    code: str
    job_type: JobType
    submitted_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def execution_time(self) -> Optional[float]:
        """
        Calculate execution time if available
        
        Returns:
            Execution time in seconds, or None if not completed
        """
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert job to dictionary for API responses
        
        Returns:
            Dictionary representation of the job
        """
        return {
            "job_id": self.id,
            "job_type": self.job_type.value,
            "status": self.status.value,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "execution_time": self.execution_time,
            "has_result": self.result is not None,
            "has_error": self.error is not None
        }


# Type variable for generic job type
T = TypeVar('T', bound=Job)


class JobProcessor(ABC):
    """
    Abstract base class defining how processors should handle jobs.
    
    The processor is responsible for:
    1. Setting job.status to RUNNING when processing begins
    2. Setting job.started_at timestamp when processing begins
    3. For successful jobs:
       - Setting job.result with the analysis results
       - Setting job.status to COMPLETED
    4. For failed jobs:
       - Setting job.error with failure information
       - Setting job.status to FAILED
    5. Setting job.completed_at timestamp when processing ends
    
    The job manager takes care of job creation, cleanup, and history management.
    """
    
    @abstractmethod
    async def process(self, job: T) -> None:
        """
        Process a job and update its state.
        
        Args:
            job: The job to process
            
        The processor should handle all exceptions internally and
        update the job status to FAILED if processing cannot complete.
        """
        pass


# Concrete job implementations
@dataclass
class LintJob(Job):
    """Job for pylint code analysis"""
    def __init__(self, job_id: str, code: str):
        super().__init__(
            id=job_id,
            status=JobStatus.PENDING,
            code=code,
            job_type=JobType.LINT,
            submitted_at=float(__import__('time').time())
        )


@dataclass
class StaticAnalysisJob(Job):
    """Job for mypy static type analysis"""
    def __init__(self, job_id: str, code: str):
        super().__init__(
            id=job_id,
            status=JobStatus.PENDING,
            code=code,
            job_type=JobType.STATIC_ANALYSIS,
            submitted_at=float(__import__('time').time())
        )
