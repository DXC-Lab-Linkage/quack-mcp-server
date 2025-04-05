"""
Processor for static type analysis of Python code using mypy.
"""

import asyncio
import logging
import tempfile
import os
import time
from typing import Dict, Any, List

from ..jobs.enums import JobStatus
from ..jobs.base import JobProcessor, StaticAnalysisJob

logger = logging.getLogger("quack")


class StaticAnalysisJobProcessor(JobProcessor):
    """Processor for static analysis jobs using mypy"""
    
    async def process(self, job: StaticAnalysisJob) -> None:
        """
        Process a static analysis job using mypy
        
        This processor:
        1. Creates a temporary file with the code
        2. Runs mypy on the file
        3. Parses the output into structured data
        4. Updates the job with results or error information
        
        The job status will be updated to COMPLETED or FAILED
        based on the outcome of the processing.
        
        Args:
            job: The static analysis job to process
        """
        # Mark job as running
        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        logger.info(f"[{job.job_type.value}:{job.id}] Starting mypy analysis")
        
        temp_path = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(job.code.encode('utf-8'))
                logger.debug(f"[{job.job_type.value}:{job.id}] Created temporary file at {temp_path}")
                
            # Run mypy
            try:
                # Try up to 3 times with exponential backoff
                for attempt in range(3):
                    try:
                        if attempt > 0:
                            logger.info(f"[{job.job_type.value}:{job.id}] Retry attempt {attempt+1}")
                            # Wait with exponential backoff
                            await asyncio.sleep(2 ** attempt)
                            
                        # Run mypy with options for machine-readable output
                        process = await asyncio.create_subprocess_exec(
                            "mypy", "--no-error-summary", "--show-column-numbers", 
                            "--show-error-codes", "--no-pretty", temp_path,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        
                        logger.debug(f"[{job.job_type.value}:{job.id}] Mypy process started with PID: {process.pid}")
                        
                        # Set a timeout for the process
                        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
                        
                        # If we get here, the process completed without timing out
                        break
                    except (OSError, asyncio.TimeoutError) as e:
                        if attempt == 2:  # Last attempt
                            raise  # Re-raise the exception
                        logger.warning(f"[{job.job_type.value}:{job.id}] Attempt {attempt+1} failed: {str(e)}")
                
                # Process results - mypy returns non-zero if it finds type errors
                mypy_output = stdout.decode().strip()
                mypy_errors = stderr.decode().strip()
                
                if mypy_errors:
                    logger.error(f"[{job.job_type.value}:{job.id}] Mypy error: {mypy_errors}")
                    job.status = JobStatus.FAILED
                    job.error = f"Mypy error: {mypy_errors}"
                    job.completed_at = time.time()
                    return
                
                # Parse mypy output
                issues: List[Dict[str, Any]] = []
                if mypy_output:
                    for line in mypy_output.splitlines():
                        parts = line.split(":", 4)
                        if len(parts) >= 4:
                            file_path, line_num, col_num, message = parts[:4]
                            try:
                                line_num = int(line_num)
                                col_num = int(col_num)
                                
                                # Extract error code if present
                                error_code = None
                                if "[" in message and "]" in message:
                                    code_part = message.split("[")[1].split("]")[0]
                                    if code_part.startswith("error-"):
                                        error_code = code_part
                                
                                # Add line content
                                line_content = None
                                if 0 <= line_num-1 < len(job.code.splitlines()):
                                    line_content = job.code.splitlines()[line_num-1]
                                
                                issues.append({
                                    "line": line_num,
                                    "column": col_num,
                                    "message": message.strip(),
                                    "error_code": error_code,
                                    "line_content": line_content
                                })
                            except (ValueError, IndexError):
                                # Skip malformed output lines
                                logger.warning(f"[{job.job_type.value}:{job.id}] Skipping malformed output line: {line}")
                                continue
                
                # Create result
                job.result = {
                    "status": "success",
                    "summary": {
                        "issue_count": len(issues)
                    },
                    "issues": issues
                }
                
                logger.info(f"[{job.job_type.value}:{job.id}] Analysis complete with {len(issues)} issues")
                job.status = JobStatus.COMPLETED
                job.completed_at = time.time()
                
            except asyncio.TimeoutError:
                logger.error(f"[{job.job_type.value}:{job.id}] Process timed out")
                job.status = JobStatus.FAILED
                job.error = "Process timed out after 30 seconds"
                job.completed_at = time.time()
                
        except Exception as e:
            logger.error(f"[{job.job_type.value}:{job.id}] Error: {str(e)}", exc_info=True)
            job.status = JobStatus.FAILED
            job.error = f"Error: {str(e)}"
            job.completed_at = time.time()
            
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    logger.debug(f"[{job.job_type.value}:{job.id}] Cleaned up temporary file: {temp_path}")
                except Exception as e:
                    logger.error(f"[{job.job_type.value}:{job.id}] Failed to clean up temporary file: {str(e)}")
