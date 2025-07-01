#!/usr/bin/env python3
"""
Test script to run basedpyright analysis on the test file.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from quack.jobs.factory import JobFactory
from quack.jobs.enums import JobType
from quack.server import create_server


async def test_basedpyright_analysis():
    """Test basedpyright analysis on our test file"""
    
    # Initialize the server to register processors
    server = create_server()
    print("Server initialized and processors registered")
    
    # Read the test file
    test_file_path = "tests/examples/basedpyright_test.py"
    with open(test_file_path, 'r') as f:
        test_code = f.read()
    
    print(f"=== Running basedpyright analysis on {test_file_path} ===")
    print(f"Code length: {len(test_code)} characters")
    print()
    
    # Create a basedpyright job
    job = JobFactory.create_job(JobType.BASEDPYRIGHT, test_code)
    print(f"Created job: {job.job_type.value}, ID: {job.id}")
    print(f"Job status: {job.status.value}")
    print()
    
    # Get the processor and run the job
    processor = JobFactory.get_processor(JobType.BASEDPYRIGHT)
    print(f"Using processor: {type(processor).__name__}")
    
    # Process the job
    await processor.process(job)
    
    # Display results
    print(f"\n=== Analysis Results ===")
    print(f"Job status: {job.status.value}")
    
    if job.status.value == "completed":
        result = job.result
        print(f"Status: {result['status']}")
        print(f"Issues found: {result['summary']['issue_count']}")
        print()
        
        if result['issues']:
            print("Issues:")
            for i, issue in enumerate(result['issues'], 1):
                print(f"  {i}. Line {issue['line']}, Column {issue['column']}: {issue['message']}")
                if issue.get('rule'):
                    print(f"     Rule: {issue['rule']}")
                if issue.get('line_content'):
                    print(f"     Code: {issue['line_content'].strip()}")
                print()
        else:
            print("No issues found!")
            
    elif job.status.value == "failed":
        print(f"Analysis failed: {job.error}")
    else:
        print(f"Unexpected status: {job.status.value}")


if __name__ == "__main__":
    asyncio.run(test_basedpyright_analysis())