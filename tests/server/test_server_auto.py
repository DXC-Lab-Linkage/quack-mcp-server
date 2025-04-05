"""
Integration test for the Quack MCP server.

This test automatically starts and stops the server using pytest fixtures.
"""

import asyncio
import json
import pytest
import subprocess
import sys
import os
import signal
from pathlib import Path

# Import job type for testing
from quack.jobs.enums import JobType

@pytest.fixture(scope="module")
def server_process():
    """Start the Quack server as a subprocess and yield the process."""
    # Get the path to the quack.py script
    quack_path = Path(__file__).parent.parent.parent / "quack.py"
    
    # Start the server process
    process = subprocess.Popen(
        [sys.executable, str(quack_path), "--debug"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Give the server a moment to start up
    import time
    time.sleep(2)
    
    # Check if the process started successfully
    if process.poll() is not None:
        print(f"Server failed to start. Exit code: {process.poll()}")
        stderr = process.stderr.read()
        print(f"Server stderr: {stderr}")
    
    # Yield the process for tests to use
    yield process
    
    # Clean up after tests
    if process.poll() is None:  # Only terminate if still running
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=5)

@pytest.mark.asyncio
async def test_server_startup_shutdown(server_process):
    """Test that the server starts up and shuts down properly."""
    # Check that the process is running
    assert server_process.poll() is None, "Server process is not running"
    
    # Check that the process has a valid PID
    assert server_process.pid > 0, "Server process has invalid PID"
    
    # Read some output to verify the server is running
    # Use a non-blocking approach with a timeout
    server_process.stdout.flush()
    
    # Check if there's any output available
    import select
    readable, _, _ = select.select([server_process.stdout], [], [], 5)
    
    if readable:
        line = server_process.stdout.readline()
        assert "Starting Quack MCP server" in line, "Server startup message not found"

@pytest.mark.asyncio
async def test_server_with_client(server_process, job_manager):
    """Test that we can use the job manager while the server is running."""
    # Check that the process is running
    assert server_process.poll() is None, "Server process is not running"
    
    # Read test code
    test_code_path = Path(__file__).parent.parent / "examples" / "example_code.py"
    with open(test_code_path, "r") as f:
        test_code = f.read()
    
    # Submit a linting job
    job = job_manager.submit_job(JobType.LINT, test_code)
    
    # Verify the job was created
    assert job.id is not None, "No job ID assigned"
    
    # Wait for the job to complete
    await asyncio.sleep(3)
    
    # Get the job
    job = job_manager.get_job(job.id)
    
    # Verify the job completed
    assert job.status.value == "completed", "Job did not complete"
    assert job.result is not None, "No results returned"
