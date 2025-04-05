"""
Processor for linting Python code using pylint.
"""

import asyncio
import json
import logging
import tempfile
import os
import time
import subprocess
import sys
from typing import Dict, Any, List

from ..jobs.enums import JobStatus
from ..jobs.base import JobProcessor, LintJob

logger = logging.getLogger("quack")


class LintJobProcessor(JobProcessor):
    """Processor for lint jobs using pylint"""
    
    async def process(self, job: LintJob) -> None:
        """
        Process a lint job using pylint
        
        This processor:
        1. Creates a temporary file with the code
        2. Runs pylint on the file
        3. Parses the JSON output
        4. Updates the job with results or error information
        
        The job status will be updated to COMPLETED or FAILED
        based on the outcome of the processing.
        
        Args:
            job: The lint job to process
        """
        # Mark job as running
        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        logger.info(f"[{job.job_type.value}:{job.id}] Starting pylint analysis")
        
        temp_path = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(job.code.encode('utf-8'))
                logger.debug(f"[{job.job_type.value}:{job.id}] Created temporary file at {temp_path}")
                
            # Run pylint using a simpler approach
            try:
                # Use a simple approach to run pylint
                logger.debug(f"[{job.job_type.value}:{job.id}] Running pylint on {temp_path}")
                
                # Create a simple Python script to run pylint
                with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as script_file:
                    script_path = script_file.name
                    script_file.write(f"""
import sys
import json
import pylint.lint

# Run pylint with JSON reporter
pylint_args = ['--output-format=json', '{temp_path}']
try:
    pylint.lint.Run(pylint_args)
except SystemExit as e:
    # Pylint calls sys.exit(), which we catch
    pass
""".encode('utf-8'))
                
                # Run the script
                logger.debug(f"[{job.job_type.value}:{job.id}] Running script: {script_path}")
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                # Log the output for debugging
                logger.debug(f"[{job.job_type.value}:{job.id}] Script stdout: {result.stdout}")
                logger.debug(f"[{job.job_type.value}:{job.id}] Script stderr: {result.stderr}")
                logger.debug(f"[{job.job_type.value}:{job.id}] Script return code: {result.returncode}")
                
                # Clean up the script file
                try:
                    os.unlink(script_path)
                except Exception as e:
                    logger.error(f"[{job.job_type.value}:{job.id}] Failed to clean up script file: {str(e)}")
                
                # Check for process errors
                if result.returncode != 0:
                    error_msg = result.stderr.strip()
                    logger.error(f"[{job.job_type.value}:{job.id}] Script failed: {error_msg}")
                    job.status = JobStatus.FAILED
                    job.error = f"Script failed: {error_msg}"
                    job.completed_at = time.time()
                    return
                
                # Process results
                lint_output = result.stdout
                logger.debug(f"[{job.job_type.value}:{job.id}] Parsing lint output: {lint_output}")
                
                # If there's no output, it means there were no issues
                if not lint_output.strip():
                    logger.info(f"[{job.job_type.value}:{job.id}] No issues found")
                    job.result = {
                        "status": "success",
                        "summary": {
                            "error_count": 0,
                            "warning_count": 0,
                            "refactor_count": 0,
                            "convention_count": 0,
                            "total_issues": 0
                        },
                        "errors": [],
                        "warnings": [],
                        "refactors": [],
                        "conventions": []
                    }
                    job.status = JobStatus.COMPLETED
                    job.completed_at = time.time()
                    return
                
                try:
                    lint_results = json.loads(lint_output) if lint_output.strip() else []
                    logger.debug(f"[{job.job_type.value}:{job.id}] Parsed lint results: {lint_results}")
                except json.JSONDecodeError as e:
                    logger.error(f"[{job.job_type.value}:{job.id}] Failed to parse JSON: {str(e)}")
                    job.status = JobStatus.FAILED
                    job.error = f"Failed to parse pylint output: {str(e)}"
                    job.completed_at = time.time()
                    return
                
                # Organize results by category
                errors: List[Dict[str, Any]] = []
                warnings: List[Dict[str, Any]] = []
                conventions: List[Dict[str, Any]] = []
                refactors: List[Dict[str, Any]] = []
                
                for message in lint_results:
                    msg_type = message.get("type", "")
                    
                    # Add line content
                    if "line" in message and "column" in message:
                        code_lines = job.code.splitlines()
                        if 0 <= message["line"]-1 < len(code_lines):
                            message["line_content"] = code_lines[message["line"]-1]
                    
                    # Categorize
                    if msg_type == "error":
                        errors.append(message)
                    elif msg_type == "warning":
                        warnings.append(message)
                    elif msg_type == "refactor":
                        refactors.append(message)
                    else:
                        conventions.append(message)
                
                # Create result
                issue_count = len(errors) + len(warnings) + len(conventions) + len(refactors)
                job.result = {
                    "status": "success",
                    "summary": {
                        "error_count": len(errors),
                        "warning_count": len(warnings),
                        "refactor_count": len(refactors),
                        "convention_count": len(conventions),
                        "total_issues": issue_count
                    },
                    "errors": errors,
                    "warnings": warnings,
                    "refactors": refactors,
                    "conventions": conventions
                }
                
                logger.info(f"[{job.job_type.value}:{job.id}] Analysis complete with {issue_count} issues")
                job.status = JobStatus.COMPLETED
                job.completed_at = time.time()
                
            except Exception as e:
                logger.error(f"[{job.job_type.value}:{job.id}] Error running pylint: {str(e)}", exc_info=True)
                job.status = JobStatus.FAILED
                job.error = f"Error running pylint: {str(e)}"
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
