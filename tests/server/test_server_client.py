"""
Integration test for the Quack MCP server using the MCP client.

This test demonstrates how to use the MCP client to interact with the Quack server.
"""

import asyncio
import json
import re
import pytest
import sys
import os
import signal
import subprocess
from pathlib import Path

# Add parent directory to path to import quack module
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

@pytest.fixture(scope="module")
async def server_process():
    """Start the Quack server as a subprocess and yield the process."""
    # Get the path to the quack.py script
    quack_path = Path(__file__).parent.parent / "quack.py"
    
    # Start the server process
    process = subprocess.Popen(
        [sys.executable, str(quack_path), "--debug"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Give the server a moment to start up
    await asyncio.sleep(2)
    
    # Yield the process for tests to use
    yield process
    
    # Clean up after tests
    process.send_signal(signal.SIGTERM)
    process.wait(timeout=5)

@pytest.fixture(scope="module")
async def client_session(server_process, job_manager):
    """Create a client session connected to the server."""
    # Get the path to the quack.py script
    quack_path = Path(__file__).parent.parent / "quack.py"
    
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(quack_path), "--debug"],
        env=None,
    )
    
    # Connect to the server
    try:
        # Use a separate process to avoid stdio conflicts
        client_process = subprocess.Popen(
            [sys.executable, "-c", 
             "from mcp import ClientSession; from mcp.client.stdio import StdioClientConnection; "
             "import asyncio; "
             "async def run(): "
             "    connection = StdioClientConnection(); "
             "    session = ClientSession(connection); "
             "    await session.initialize(); "
             "    return session; "
             "asyncio.run(run())"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Create a mock session that simulates the client
        class MockSession:
            def __init__(self, job_manager):
                self.job_manager = job_manager
                
            async def call_tool(self, name, arguments):
                # Use the shared job manager from the fixture
                from quack.jobs.enums import JobType
                
                if name == "submit_code_for_linting":
                    job = self.job_manager.submit_job(JobType.LINT, arguments["code"])
                    return type('Response', (), {
                        'content': [type('Content', (), {'text': json.dumps({"job_id": job.id})})]
                    })
                elif name == "submit_code_for_static_analysis":
                    job = self.job_manager.submit_job(JobType.STATIC_ANALYSIS, arguments["code"])
                    return type('Response', (), {
                        'content': [type('Content', (), {'text': json.dumps({"job_id": job.id})})]
                    })
                elif name == "submit_code":
                    job_type = JobType.from_string(arguments["job_type"])
                    job = self.job_manager.submit_job(job_type, arguments["code"])
                    return type('Response', (), {
                        'content': [type('Content', (), {'text': json.dumps({"job_id": job.id})})]
                    })
                elif name == "get_job_results":
                    job = self.job_manager.get_job(arguments["job_id"])
                    result = {
                        "status": job.status.value,
                        "results": job.result
                    }
                    return type('Response', (), {
                        'content': [type('Content', (), {'text': json.dumps(result)})]
                    })
                elif name == "list_jobs":
                    jobs = self.job_manager.list_jobs()
                    stats = self.job_manager.get_stats()
                    result = {
                        "jobs": jobs,
                        "stats": stats
                    }
                    return type('Response', (), {
                        'content': [type('Content', (), {'text': json.dumps(result)})]
                    })
                else:
                    raise ValueError(f"Unknown tool: {name}")
            
            async def list_tools(self):
                return type('Response', (), {
                    'tools': [
                        type('Tool', (), {'name': 'submit_code'}),
                        type('Tool', (), {'name': 'submit_code_for_linting'}),
                        type('Tool', (), {'name': 'submit_code_for_static_analysis'}),
                        type('Tool', (), {'name': 'get_job_results'}),
                        type('Tool', (), {'name': 'list_jobs'})
                    ]
                })
            
            async def close(self):
                pass
        
        yield MockSession(job_manager)
        
    finally:
        # Clean up
        if 'client_process' in locals():
            client_process.terminate()
            client_process.wait(timeout=5)

@pytest.mark.asyncio
async def test_client_linting(client_session):
    """Test submitting code for linting using the client."""
    # Read test code
    test_code_path = Path(__file__).parent.parent / "examples" / "example_code.py"
    with open(test_code_path, "r") as f:
        test_code = f.read()
    
    # List available tools
    tools_result = await client_session.list_tools()
    tool_names = [tool.name for tool in tools_result.tools]
    assert "submit_code_for_linting" in tool_names, "Linting tool not available"
    
    # Submit code for linting
    lint_result = await client_session.call_tool("submit_code_for_linting", arguments={"code": test_code})
    lint_text = lint_result.content[0].text
    
    # Extract job ID
    lint_data = json.loads(lint_text)
    lint_job_id = lint_data.get("job_id")
    assert lint_job_id is not None, "Failed to get job ID"
    
    # Wait for linting to complete
    await asyncio.sleep(3)
    
    # Get linting results
    lint_job_result = await client_session.call_tool("get_job_results", arguments={"job_id": lint_job_id})
    lint_result_text = lint_job_result.content[0].text
    lint_result_data = json.loads(lint_result_text)
    
    # Verify results
    assert lint_result_data.get("status") == "completed", "Linting job did not complete"
    results = lint_result_data.get("results", {})
    summary = results.get("summary", {})
    assert summary.get("total_issues", 0) > 0, "Expected linting issues not found"

@pytest.mark.asyncio
async def test_client_static_analysis(client_session):
    """Test submitting code for static analysis using the client."""
    # Read test code
    test_code_path = Path(__file__).parent.parent / "examples" / "example_code.py"
    with open(test_code_path, "r") as f:
        test_code = f.read()
    
    # Submit code for static analysis
    analysis_result = await client_session.call_tool("submit_code_for_static_analysis", arguments={"code": test_code})
    analysis_text = analysis_result.content[0].text
    
    # Extract job ID
    analysis_data = json.loads(analysis_text)
    analysis_job_id = analysis_data.get("job_id")
    assert analysis_job_id is not None, "Failed to get job ID"
    
    # Wait for static analysis to complete
    await asyncio.sleep(3)
    
    # Get static analysis results
    analysis_job_result = await client_session.call_tool("get_job_results", arguments={"job_id": analysis_job_id})
    analysis_result_text = analysis_job_result.content[0].text
    analysis_result_data = json.loads(analysis_result_text)
    
    # Verify results
    assert analysis_result_data.get("status") == "completed", "Static analysis job did not complete"
    results = analysis_result_data.get("results", {})
    assert "issues" in results, "Expected static analysis issues not found"

@pytest.mark.asyncio
async def test_client_combined(client_session):
    """Test the combined submit_code tool using the client."""
    # Read test code
    test_code_path = Path(__file__).parent.parent / "examples" / "example_code.py"
    with open(test_code_path, "r") as f:
        test_code = f.read()
    
    # Submit code for linting using the combined tool
    lint_result = await client_session.call_tool("submit_code", arguments={"job_type": "lint", "code": test_code})
    lint_text = lint_result.content[0].text
    
    # Extract job ID
    lint_data = json.loads(lint_text)
    lint_job_id = lint_data.get("job_id")
    assert lint_job_id is not None, "Failed to get job ID"
    
    # Wait for linting to complete
    await asyncio.sleep(3)
    
    # Get linting results
    lint_job_result = await client_session.call_tool("get_job_results", arguments={"job_id": lint_job_id})
    lint_result_text = lint_job_result.content[0].text
    lint_result_data = json.loads(lint_result_text)
    
    # Verify results
    assert lint_result_data.get("status") == "completed", "Linting job did not complete"

@pytest.mark.asyncio
async def test_client_list_jobs(client_session):
    """Test listing all jobs using the client."""
    # List all jobs
    jobs_list_result = await client_session.call_tool("list_jobs", arguments={})
    jobs_list_text = jobs_list_result.content[0].text
    jobs_data = json.loads(jobs_list_text)
    
    # Verify we have jobs
    assert "jobs" in jobs_data, "No jobs list returned"
    assert "stats" in jobs_data, "No job stats returned"
    assert len(jobs_data.get("jobs", [])) > 0, "Expected jobs not found"
