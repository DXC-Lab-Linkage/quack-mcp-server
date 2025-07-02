"""
Tests for the BasedPyright static analysis processor.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from quack.jobs.base import BasedPyrightJob
from quack.jobs.enums import JobStatus
from quack.processors.basedpyright import BasedPyrightJobProcessor


@pytest.fixture
def basedpyright_processor():
    """Create a BasedPyright processor for testing"""
    return BasedPyrightJobProcessor()


@pytest.fixture
def sample_basedpyright_job():
    """Create a sample BasedPyright job for testing"""
    code = """def greet(name: str) -> str:
    return f"Hello, {name}!"

# This should cause a type error
result = greet(123)
"""
    return BasedPyrightJob("test-job-123", code)


@pytest.mark.asyncio
async def test_basedpyright_processor_success(
    basedpyright_processor, sample_basedpyright_job
):
    """Test successful basedpyright analysis with type errors found"""
    # Mock JSON output that basedpyright might produce
    mock_json_output = """{
        "generalDiagnostics": [
            {
                "message": "Argument of type 'Literal[123]' cannot be assigned to parameter 'name' of type 'str'",
                "severity": "error",
                "range": {
                    "start": {"line": 4, "character": 14},
                    "end": {"line": 4, "character": 17}
                },
                "code": "reportArgumentType"
            }
        ]
    }"""

    mock_process = AsyncMock()
    mock_process.communicate.return_value = (mock_json_output.encode(), b"")
    mock_process.pid = 12345

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch(
            "quack.processors.basedpyright.filter_and_output_json"
        ) as mock_filter:
            mock_filter.return_value = {
                "diagnostics": [
                    {
                        "message": "Argument of type 'Literal[123]' cannot be assigned to parameter 'name' of type 'str'",
                        "severity": "error",
                        "range": {
                            "start": {"line": 4, "character": 14},
                            "end": {"line": 4, "character": 17},
                        },
                        "code": "reportArgumentType",
                    }
                ]
            }
            await basedpyright_processor.process(sample_basedpyright_job)

    # Check that the job completed successfully
    assert sample_basedpyright_job.status == JobStatus.COMPLETED
    assert sample_basedpyright_job.error is None
    assert sample_basedpyright_job.result is not None
    assert sample_basedpyright_job.started_at is not None
    assert sample_basedpyright_job.completed_at is not None

    # Check the result structure
    result = sample_basedpyright_job.result
    assert result["status"] == "success"
    assert result["summary"]["filtered_issue_count"] == 1
    assert len(result["issues"]) == 1

    # Check the issue details
    issue = result["issues"][0]
    assert issue["line"] == 5  # 1-based line number
    assert issue["column"] == 15  # 1-based column number
    assert "cannot be assigned" in issue["message"]
    assert issue["severity"] == "error"
    assert issue["rule"] == "reportArgumentType"


@pytest.mark.asyncio
async def test_basedpyright_processor_no_issues(basedpyright_processor):
    """Test basedpyright analysis with no type errors"""
    code = """def greet(name: str) -> str:
    return f"Hello, {name}!"

result = greet("World")
"""
    job = BasedPyrightJob("test-job-no-issues", code)

    # Mock empty JSON output (no issues)
    mock_json_output = '{"generalDiagnostics": []}'

    mock_process = AsyncMock()
    mock_process.communicate.return_value = (mock_json_output.encode(), b"")
    mock_process.pid = 12345

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch(
            "quack.processors.basedpyright.filter_and_output_json"
        ) as mock_filter:
            mock_filter.return_value = {"diagnostics": []}
            await basedpyright_processor.process(job)

    # Check that the job completed successfully with no issues
    assert job.status == JobStatus.COMPLETED
    assert job.error is None
    assert job.result is not None

    result = job.result
    assert result["status"] == "success"
    assert result["summary"]["filtered_issue_count"] == 0
    assert len(result["issues"]) == 0


@pytest.mark.asyncio
async def test_basedpyright_processor_stderr_error(
    basedpyright_processor, sample_basedpyright_job
):
    """Test basedpyright processor when stderr contains errors"""
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (
        b"",
        b"basedpyright: command not found",
    )
    mock_process.pid = 12345

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        await basedpyright_processor.process(sample_basedpyright_job)

    # Check that the job failed
    assert sample_basedpyright_job.status == JobStatus.FAILED
    assert "basedpyright: command not found" in sample_basedpyright_job.error
    assert sample_basedpyright_job.result is None


@pytest.mark.asyncio
async def test_basedpyright_processor_timeout(
    basedpyright_processor, sample_basedpyright_job
):
    """Test basedpyright processor timeout handling"""
    mock_process = AsyncMock()
    mock_process.communicate.side_effect = asyncio.TimeoutError()
    mock_process.pid = 12345

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
            await basedpyright_processor.process(sample_basedpyright_job)

    # Check that the job failed due to timeout
    assert sample_basedpyright_job.status == JobStatus.FAILED
    assert "timed out" in sample_basedpyright_job.error
    assert sample_basedpyright_job.result is None


@pytest.mark.asyncio
async def test_basedpyright_processor_invalid_json(
    basedpyright_processor, sample_basedpyright_job
):
    """Test basedpyright processor with invalid JSON output"""
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"invalid json output", b"")
    mock_process.pid = 12345

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        await basedpyright_processor.process(sample_basedpyright_job)

    # Should still complete but handle the invalid JSON gracefully
    assert sample_basedpyright_job.status == JobStatus.COMPLETED
    assert sample_basedpyright_job.error is None
    assert sample_basedpyright_job.result is not None

    # Should have one issue with the raw output
    result = sample_basedpyright_job.result
    assert result["summary"]["filtered_issue_count"] == 1
    assert "Raw output" in result["issues"][0]["message"]


@pytest.mark.asyncio
async def test_basedpyright_processor_retry_logic(
    basedpyright_processor, sample_basedpyright_job
):
    """Test basedpyright processor retry logic on OSError"""
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b'{"generalDiagnostics": []}', b"")
    mock_process.pid = 12345

    # Mock OSError on first two attempts, success on third
    side_effects = [
        OSError("Connection failed"),
        OSError("Connection failed"),
        mock_process,
    ]

    with patch("asyncio.create_subprocess_exec", side_effect=side_effects):
        with patch("asyncio.sleep"):  # Speed up the test by mocking sleep
            with patch(
                "quack.processors.basedpyright.filter_and_output_json"
            ) as mock_filter:
                mock_filter.return_value = {"diagnostics": []}
                await basedpyright_processor.process(sample_basedpyright_job)

    # Should succeed after retries
    assert sample_basedpyright_job.status == JobStatus.COMPLETED
    assert sample_basedpyright_job.error is None


@pytest.mark.asyncio
async def test_basedpyright_processor_retry_exhausted(
    basedpyright_processor, sample_basedpyright_job
):
    """Test basedpyright processor when all retry attempts fail"""
    with patch(
        "asyncio.create_subprocess_exec",
        side_effect=OSError("Persistent error"),
    ):
        with patch("asyncio.sleep"):  # Speed up the test by mocking sleep
            await basedpyright_processor.process(sample_basedpyright_job)

    # Should fail after all retries are exhausted
    assert sample_basedpyright_job.status == JobStatus.FAILED
    assert "Persistent error" in sample_basedpyright_job.error
