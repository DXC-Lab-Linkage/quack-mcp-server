"""
Pytest configuration for Quack tests.
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path to import quack module
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import server-related modules
from quack.jobs.manager import JobManager
from quack.jobs.enums import JobType
from quack.processors.lint import LintJobProcessor
from quack.processors.static_analysis import StaticAnalysisJobProcessor
from quack.jobs.factory import JobFactory

# Register processors for testing
JobFactory.register_processor(JobType.LINT, LintJobProcessor())
JobFactory.register_processor(JobType.STATIC_ANALYSIS, StaticAnalysisJobProcessor())

# Set asyncio mode
pytest_plugins = ["pytest_asyncio"]

# Use pytest-asyncio's built-in event_loop fixture

@pytest.fixture(scope="session")
def job_manager():
    """Create a job manager for testing."""
    return JobManager()
