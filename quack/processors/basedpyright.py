"""
Processor for static type analysis of Python code using basedpyright.
"""

import asyncio
import json
import logging
import tempfile
import os
import time
from typing import Dict, Any, List

from ..jobs.enums import JobStatus
from ..jobs.base import JobProcessor, BasedPyrightJob

logger = logging.getLogger("quack")


class BasedPyrightJobProcessor(JobProcessor):
    """Processor for static analysis jobs using basedpyright"""

    async def process(self, job: BasedPyrightJob) -> None:
        """
        Process a static analysis job using basedpyright

        This processor:
        1. Creates a temporary file with the code
        2. Runs basedpyright on the file with JSON output
        3. Parses the JSON output into structured data
        4. Updates the job with results or error information

        The job status will be updated to COMPLETED or FAILED
        based on the outcome of the processing.

        Args:
            job: The basedpyright analysis job to process
        """
        # Mark job as running
        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        logger.info(f"[{job.job_type.value}:{job.id}] Starting basedpyright analysis")

        temp_path = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(job.code.encode("utf-8"))
                logger.debug(
                    f"[{job.job_type.value}:{job.id}] Created temporary file at {temp_path}"
                )

            # Run basedpyright
            try:
                # Try up to 3 times with exponential backoff
                for attempt in range(3):
                    try:
                        if attempt > 0:
                            logger.info(
                                f"[{job.job_type.value}:{job.id}] Retry attempt {attempt + 1}"
                            )
                            # Wait with exponential backoff
                            await asyncio.sleep(2**attempt)

                        # Run basedpyright with JSON output
                        process = await asyncio.create_subprocess_exec(
                            "basedpyright",
                            "--outputjson",
                            temp_path,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )

                        logger.debug(
                            f"[{job.job_type.value}:{job.id}] BasedPyright process started with PID: {process.pid}"
                        )

                        # Set a timeout for the process
                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(), timeout=30.0
                        )

                        # If we get here, the process completed without timing out
                        break
                    except (OSError, asyncio.TimeoutError) as e:
                        if attempt == 2:  # Last attempt
                            raise  # Re-raise the exception
                        logger.warning(
                            f"[{job.job_type.value}:{job.id}] Attempt {attempt + 1} failed: {str(e)}"
                        )

                # Process results - basedpyright returns non-zero if it finds type errors
                basedpyright_output = stdout.decode().strip()
                basedpyright_errors = stderr.decode().strip()

                if basedpyright_errors:
                    logger.error(
                        f"[{job.job_type.value}:{job.id}] BasedPyright error: {basedpyright_errors}"
                    )
                    job.status = JobStatus.FAILED
                    job.error = f"BasedPyright error: {basedpyright_errors}"
                    job.completed_at = time.time()
                    return

                # Parse basedpyright JSON output
                issues: List[Dict[str, Any]] = []
                if basedpyright_output:
                    try:
                        # BasedPyright outputs JSON format
                        json_data = json.loads(basedpyright_output)
                        
                        # Handle different JSON structures that basedpyright might return
                        diagnostics = []
                        if isinstance(json_data, dict):
                            # BasedPyright uses "generalDiagnostics" key
                            diagnostics = json_data.get("generalDiagnostics", json_data.get("diagnostics", []))
                        elif isinstance(json_data, list):
                            diagnostics = json_data

                        for diagnostic in diagnostics:
                            if isinstance(diagnostic, dict):
                                # Extract information from diagnostic
                                message = diagnostic.get("message", "")
                                severity = diagnostic.get("severity", "error")
                                
                                # Get position information
                                range_info = diagnostic.get("range", {})
                                start_pos = range_info.get("start", {})
                                line_num = start_pos.get("line", 0) + 1  # Convert 0-based to 1-based
                                col_num = start_pos.get("character", 0) + 1  # Convert 0-based to 1-based
                                
                                # Get rule/code if available
                                rule = diagnostic.get("code", diagnostic.get("rule", None))
                                
                                # Add line content
                                line_content = None
                                if 0 <= line_num - 1 < len(job.code.splitlines()):
                                    line_content = job.code.splitlines()[line_num - 1]

                                issues.append({
                                    "line": line_num,
                                    "column": col_num,
                                    "message": message,
                                    "severity": severity,
                                    "rule": rule,
                                    "line_content": line_content,
                                })
                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"[{job.job_type.value}:{job.id}] Failed to parse JSON output: {str(e)}"
                        )
                        # Fall back to treating output as plain text
                        if basedpyright_output:
                            issues.append({
                                "line": 1,
                                "column": 1,
                                "message": f"Raw output: {basedpyright_output}",
                                "severity": "error",
                                "rule": None,
                                "line_content": None,
                            })

                # Create result
                job.result = {
                    "status": "success",
                    "summary": {"issue_count": len(issues)},
                    "issues": issues,
                }

                logger.info(
                    f"[{job.job_type.value}:{job.id}] Analysis complete with {len(issues)} issues"
                )
                job.status = JobStatus.COMPLETED
                job.completed_at = time.time()

            except asyncio.TimeoutError:
                logger.error(f"[{job.job_type.value}:{job.id}] Process timed out")
                job.status = JobStatus.FAILED
                job.error = "Process timed out after 30 seconds"
                job.completed_at = time.time()

        except Exception as e:
            logger.error(
                f"[{job.job_type.value}:{job.id}] Error: {str(e)}", exc_info=True
            )
            job.status = JobStatus.FAILED
            job.error = f"Error: {str(e)}"
            job.completed_at = time.time()

        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    logger.debug(
                        f"[{job.job_type.value}:{job.id}] Cleaned up temporary file: {temp_path}"
                    )
                except Exception as e:
                    logger.error(
                        f"[{job.job_type.value}:{job.id}] Failed to clean up temporary file: {str(e)}"
                    )