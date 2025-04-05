"""
Test for the lint processor.

This file tests the lint processor functionality.
"""

import pytest
from pathlib import Path

from quack.processors.lint import LintJobProcessor
from quack.jobs.enums import JobStatus, JobType
from quack.jobs.base import LintJob

def test_lint_processor_initialization():
    """Test that the lint processor can be initialized."""
    processor = LintJobProcessor()
    assert processor is not None

def test_lint_processor_process():
    """Test that the lint processor can process code."""
    # Get the example code
    example_code_path = Path(__file__).parent.parent / "examples" / "example_code.py"
    with open(example_code_path, "r") as f:
        code = f.read()
    
    # Create a lint job
    job = LintJob(job_id="test-job-1", code=code)
    
    # Process the job
    processor = LintJobProcessor()
    import asyncio
    asyncio.run(processor.process(job))
    
    # Check the result
    result = job.result
    
    # Check the result
    assert result is not None
    assert "summary" in result
    assert "errors" in result
    assert "warnings" in result
    assert "refactors" in result
    assert "conventions" in result
    
    # We expect issues in the example code
    assert result["summary"]["total_issues"] > 0
