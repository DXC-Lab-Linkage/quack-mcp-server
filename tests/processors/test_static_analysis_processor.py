"""
Test for the static analysis processor.

This file tests the static analysis processor functionality.
"""

import pytest
from pathlib import Path

from quack.processors.static_analysis import StaticAnalysisJobProcessor
from quack.jobs.enums import JobStatus, JobType
from quack.jobs.base import StaticAnalysisJob

def test_static_analysis_processor_initialization():
    """Test that the static analysis processor can be initialized."""
    processor = StaticAnalysisJobProcessor()
    assert processor is not None

def test_static_analysis_processor_process():
    """Test that the static analysis processor can process code."""
    # Get the example code
    example_code_path = Path(__file__).parent.parent / "examples" / "example_code.py"
    with open(example_code_path, "r") as f:
        code = f.read()
    
    # Create a static analysis job
    job = StaticAnalysisJob(job_id="test-job-2", code=code)
    
    # Process the job
    processor = StaticAnalysisJobProcessor()
    import asyncio
    asyncio.run(processor.process(job))
    
    # Check the result
    result = job.result
    
    # Check the result
    assert result is not None
    assert "issues" in result
    
    # We expect issues in the example code
    assert len(result["issues"]) > 0
