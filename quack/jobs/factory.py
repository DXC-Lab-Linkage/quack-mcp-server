"""
Factory for creating jobs and processors.
"""

import uuid
from typing import Dict, Optional

from .enums import JobType
from .base import Job, JobProcessor, LintJob, StaticAnalysisJob, BasedPyrightJob


class JobFactory:
    """Factory for creating appropriate job types and processors"""

    # Registry of job processors by job type
    processors: Dict[JobType, JobProcessor] = {}

    @classmethod
    def register_processor(cls, job_type: JobType, processor: JobProcessor) -> None:
        """
        Register a processor for a job type

        Args:
            job_type: Type of job
            processor: Processor implementation
        """
        cls.processors[job_type] = processor

    @classmethod
    def create_job(cls, job_type: JobType, code: str, severity: str = "all", top_n: Optional[int] = None) -> Job:
        """
        Create a job of the specified type

        Args:
            job_type: Type of job to create
            code: Python code to analyze
            severity: Severity filter for basedpyright jobs ("error", "warning", "info", or "all")
            top_n: Maximum number of issues to return for basedpyright jobs

        Returns:
            A new job instance of the appropriate type

        Raises:
            ValueError: If the job type is unknown
        """
        job_id = uuid.uuid4().hex

        if job_type == JobType.LINT:
            return LintJob(job_id, code)
        elif job_type == JobType.STATIC_ANALYSIS:
            return StaticAnalysisJob(job_id, code)
        elif job_type == JobType.BASEDPYRIGHT:
            return BasedPyrightJob(job_id, code, severity, top_n)
        else:
            raise ValueError(f"Unknown job type: {job_type}")

    @classmethod
    def get_processor(cls, job_type: JobType) -> JobProcessor:
        """
        Get the processor for a job type

        Args:
            job_type: Type of job

        Returns:
            The processor for the specified job type

        Raises:
            ValueError: If no processor is registered for the job type
        """
        processor = cls.processors.get(job_type)
        if not processor:
            raise ValueError(f"No processor registered for job type: {job_type}")
        return processor
