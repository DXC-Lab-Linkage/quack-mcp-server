"""
Direct integration test for the Quack MCP server.

This test directly imports the server module for testing.
"""

import asyncio
import pytest
from pathlib import Path

# Import job type for testing
from quack.jobs.enums import JobType


@pytest.mark.asyncio
async def test_lint_job(job_manager):
    """Test submitting a linting job."""
    # Read test code
    test_code_path = Path(__file__).parent.parent / "examples" / "example_code.py"
    with open(test_code_path, "r") as f:
        test_code = f.read()

    # Submit a linting job
    job = job_manager.submit_job(JobType.LINT, test_code)

    # Verify the job was created
    assert job.id is not None, "No job ID assigned"
    assert job.job_type == JobType.LINT, "Wrong job type"

    # Wait for the job to complete
    await asyncio.sleep(3)

    # Get the job
    job = job_manager.get_job(job.id)

    # Verify the job completed
    assert job.status.value == "completed", "Job did not complete"
    assert job.result is not None, "No results returned"

    # Verify we have linting results
    summary = job.result.get("summary", {})
    assert summary.get("total_issues", 0) > 0, "Expected linting issues not found"


@pytest.mark.asyncio
async def test_static_analysis_job(job_manager):
    """Test submitting a static analysis job."""
    # Read test code
    test_code_path = Path(__file__).parent.parent / "examples" / "example_code.py"
    with open(test_code_path, "r") as f:
        test_code = f.read()

    # Submit a static analysis job
    job = job_manager.submit_job(JobType.STATIC_ANALYSIS, test_code)

    # Verify the job was created
    assert job.id is not None, "No job ID assigned"
    assert job.job_type == JobType.STATIC_ANALYSIS, "Wrong job type"

    # Wait for the job to complete
    await asyncio.sleep(3)

    # Get the job
    job = job_manager.get_job(job.id)

    # Verify the job completed
    assert job.status.value == "completed", "Job did not complete"
    assert job.result is not None, "No results returned"

    # Verify we have static analysis results
    assert "issues" in job.result, "Expected static analysis issues not found"


@pytest.mark.asyncio
async def test_job_listing(job_manager):
    """Test listing jobs."""
    # List all jobs
    jobs = job_manager.list_jobs()

    # Verify we have jobs
    assert len(jobs) > 0, "No jobs found"

    # Get stats
    stats = job_manager.get_stats()

    # Verify we have stats
    assert "by_status" in stats, "No status stats returned"
    assert "by_type" in stats, "No type stats returned"
