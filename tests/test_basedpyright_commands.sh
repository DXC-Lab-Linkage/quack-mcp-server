#!/bin/bash

# Test script for basedpyright integration
# Expected outputs are provided as comments

echo "Running basedpyright integration tests..."

# Test 1: Run the basedpyright processor tests
echo "=== Test 1: BasedPyright Processor Unit Tests ==="
python -m pytest tests/processors/test_basedpyright_processor.py -v
# Expected: All tests should pass, showing basedpyright processor works correctly

# Test 2: Test job factory can create basedpyright jobs
echo "=== Test 2: Job Factory BasedPyright Job Creation ==="
python -c "
from quack.jobs.factory import JobFactory
from quack.jobs.enums import JobType
job = JobFactory.create_job(JobType.BASEDPYRIGHT, 'def test(): pass')
print(f'Created job: {job.job_type.value}, ID: {job.id}')
assert job.job_type == JobType.BASEDPYRIGHT
print('✓ Job factory test passed')
"
# Expected: Should print job creation details and success message

# Test 3: Test that basedpyright is in the JobType enum
echo "=== Test 3: JobType Enum Contains BASEDPYRIGHT ==="
python -c "
from quack.jobs.enums import JobType
print('Available job types:', [t.value for t in JobType])
assert JobType.BASEDPYRIGHT.value == 'basedpyright'
print('✓ JobType enum test passed')
"
# Expected: Should show all job types including 'basedpyright' and pass assertion

# Test 4: Test server integration (if basedpyright is available)
echo "=== Test 4: Server Integration Test ==="
python -c "
from quack.server import create_server
from quack.jobs.enums import JobType
from quack.jobs.factory import JobFactory

server = create_server()
print('Server created successfully')

# Check if processor is registered
try:
    processor = JobFactory.get_processor(JobType.BASEDPYRIGHT)
    print(f'✓ BasedPyright processor registered: {type(processor).__name__}')
except ValueError as e:
    print(f'✗ Processor not registered: {e}')
    exit(1)
"
# Expected: Should create server and confirm basedpyright processor is registered

# Test 5: Test string conversion for job type
echo "=== Test 5: JobType String Conversion ==="
python -c "
from quack.jobs.enums import JobType
job_type = JobType.from_string('basedpyright')
print(f'Converted string to JobType: {job_type}')
assert job_type == JobType.BASEDPYRIGHT
print('✓ String conversion test passed')
"
# Expected: Should convert string 'basedpyright' to JobType.BASEDPYRIGHT

echo "All basedpyright integration tests completed!"