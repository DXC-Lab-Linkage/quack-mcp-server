"""
Enumerations for job types and statuses.
"""

from enum import Enum


class JobType(Enum):
    """Enum of supported job types"""
    LINT = "lint"
    STATIC_ANALYSIS = "static_analysis"
    
    @classmethod
    def from_string(cls, value: str) -> "JobType":
        """
        Convert string to JobType, with validation
        
        Args:
            value: String representation of job type
            
        Returns:
            JobType enum value
            
        Raises:
            ValueError: If the string doesn't match a valid job type
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_types = ", ".join([t.value for t in cls])
            raise ValueError(f"Invalid job type: '{value}'. Valid types are: {valid_types}")


class JobStatus(Enum):
    """Enum of possible job statuses"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    
    def is_terminal(self) -> bool:
        """
        Check if this is a terminal status
        
        Returns:
            True if the status is terminal (completed or failed)
        """
        return self in (JobStatus.COMPLETED, JobStatus.FAILED)
