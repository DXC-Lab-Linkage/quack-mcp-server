"""
MCP server implementation for Quack.
"""

import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP, Context

from .jobs.enums import JobType, JobStatus
from .jobs.manager import JobManager
from .jobs.factory import JobFactory
from .processors.lint import LintJobProcessor
from .processors.static_analysis import StaticAnalysisJobProcessor

logger = logging.getLogger("quack")


# Lifespan context manager for initializing the job manager
@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """
    Manage server startup and shutdown lifecycle.
    
    Args:
        server: The FastMCP server instance
        
    Yields:
        Dictionary with initialized resources
    """
    # Initialize resources on startup
    job_manager = JobManager()
    logger.info("[Server] Job manager initialized")
    
    try:
        yield {"job_manager": job_manager}
    finally:
        # Clean up on shutdown (if needed)
        logger.info("[Server] Shutting down")


def create_server() -> FastMCP:
    """
    Create and configure the Quack MCP server
    
    Returns:
        Configured FastMCP server instance
    """
    # Create the MCP server with lifespan
    mcp = FastMCP("Quack", lifespan=server_lifespan)
    
    # Register processors
    JobFactory.register_processor(JobType.LINT, LintJobProcessor())
    JobFactory.register_processor(JobType.STATIC_ANALYSIS, StaticAnalysisJobProcessor())
    
    # Generic job submission tool
    @mcp.tool()
    async def submit_code(job_type: str, code: str, ctx: Context) -> Dict[str, Any]:
        """
        Submit Python code for analysis
        
        Args:
            job_type: Type of analysis to perform ("lint" or "static_analysis")
            code: Python code content to analyze
            
        Returns:
            Dictionary with job ID for checking results later
        """
        job_manager = ctx.request_context.lifespan_context["job_manager"]
        
        # Validate job type
        try:
            job_type_enum = JobType.from_string(job_type)
        except ValueError as e:
            logger.warning(f"[Server] Invalid job type: {job_type}")
            return {
                "status": "error",
                "message": str(e)
            }
        
        # Submit job
        job = job_manager.submit_job(job_type_enum, code)
        
        logger.info(f"[{job.job_type.value}:{job.id}] Submitted new job ({len(code)} bytes)")
        
        return {
            "status": "accepted",
            "job_id": job.id,
            "job_type": job.job_type.value,
            "message": f"Code submitted for {job_type}. Use get_job_results to check status."
        }
    
    # Convenience tools for specific types
    @mcp.tool()
    async def submit_code_for_linting(code: str, ctx: Context) -> Dict[str, Any]:
        """
        Submit Python code for linting analysis
        
        Args:
            code: Python code content to analyze
            
        Returns:
            Dictionary with job ID for checking results later
        """
        # Reuse generic submit_code tool with "lint" type
        return await submit_code("lint", code, ctx)
    
    @mcp.tool()
    async def submit_code_for_static_analysis(code: str, ctx: Context) -> Dict[str, Any]:
        """
        Submit Python code for static type analysis
        
        Args:
            code: Python code content to analyze
            
        Returns:
            Dictionary with job ID for checking results later
        """
        # Reuse generic submit_code tool with "static_analysis" type
        return await submit_code("static_analysis", code, ctx)
    
    # Get job results tool
    @mcp.tool()
    async def get_job_results(job_id: str, ctx: Context) -> Dict[str, Any]:
        """
        Get the results of a previously submitted job
        
        Args:
            job_id: ID of the job
            
        Returns:
            Dictionary with job status and results if available
        """
        job_manager = ctx.request_context.lifespan_context["job_manager"]
        job = job_manager.get_job(job_id)
        
        if not job:
            logger.warning(f"[Job] Requested unknown job: {job_id}")
            return {
                "status": "error",
                "message": f"No job found with ID: {job_id}"
            }
        
        logger.info(f"[{job.job_type.value}:{job_id}] Status check: {job.status.value}")
        
        # Return appropriate response based on job status
        if job.status == JobStatus.COMPLETED:
            return {
                "status": "completed",
                "job_type": job.job_type.value,
                "results": job.result,
                "execution_time": job.execution_time
            }
        elif job.status == JobStatus.FAILED:
            return {
                "status": "failed",
                "job_type": job.job_type.value,
                "error": job.error,
                "execution_time": job.execution_time
            }
        else:
            # Still in progress
            return {
                "status": job.status.value,
                "job_type": job.job_type.value,
                "message": f"Job is {job.status.value}. Please check again later."
            }
    
    # List jobs tool
    @mcp.tool()
    async def list_jobs(ctx: Context, job_type: Optional[str] = None) -> Dict[str, Any]:
        """
        List all jobs and their statuses
        
        Args:
            ctx: Context object
            job_type: Optional filter for job type
            
        Returns:
            Dictionary with list of jobs and their statuses
        """
        job_manager = ctx.request_context.lifespan_context["job_manager"]
        
        # Convert string job type to enum if provided
        job_type_enum = None
        if job_type:
            try:
                job_type_enum = JobType.from_string(job_type)
            except ValueError:
                return {
                    "status": "error",
                    "message": f"Invalid job type: {job_type}"
                }
        
        return {
            "jobs": job_manager.list_jobs(job_type_enum),
            "stats": job_manager.get_stats()
        }
    
    return mcp
