"""
Processor for static type analysis of Python code using basedpyright.
"""

import asyncio
import json
import logging
import tempfile
import os
import subprocess
import sys
import time
from typing import Dict, Any, List

from ..jobs.enums import JobStatus
from ..jobs.base import JobProcessor, BasedPyrightJob
from ..utils.diagnostics import filter_and_output_json

logger = logging.getLogger("quack")


def is_basedpyright_installed():
    """Check if basedpyright is installed and available."""
    try:
        subprocess.run(
            ["basedpyright", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_basedpyright():
    """Install basedpyright using pip."""
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "basedpyright"], check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install basedpyright: {e}")
        raise


def log_config_detection(verbose=False):
    """Log configuration file detection for basedpyright in verbose mode."""
    if not verbose:
        return
        
    # Get project root - go up from quack/processors/ to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Determine which config file takes precedence
    pyright_config = os.path.join(project_root, "pyrightconfig.json")
    pyproject_toml = os.path.join(project_root, "pyproject.toml")

    config_used = None
    if os.path.isfile(pyright_config):
        config_used = pyright_config
    elif os.path.isfile(pyproject_toml):
        config_used = pyproject_toml
    else:
        logger.debug("No configuration file found. Using default settings.")

    if config_used:
        logger.debug(f"Using configuration from: {config_used}")


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

        # Ensure basedpyright is installed
        if not is_basedpyright_installed():
            logger.info(f"[{job.job_type.value}:{job.id}] basedpyright not found. Installing...")
            try:
                install_basedpyright()
            except Exception as e:
                logger.error(f"[{job.job_type.value}:{job.id}] Failed to install basedpyright: {e}")
                job.status = JobStatus.FAILED
                job.error = f"Failed to install basedpyright: {e}"
                job.completed_at = time.time()
                return

        # Log configuration detection in verbose mode
        verbose_mode = logger.isEnabledFor(logging.DEBUG)
        log_config_detection(verbose_mode)

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

                # Parse basedpyright JSON output and apply filtering
                if basedpyright_output:
                    try:
                        # BasedPyright outputs JSON format
                        json_data = json.loads(basedpyright_output)
                        
                        # Use the utility function to filter and format diagnostics
                        filtered_result = filter_and_output_json(json_data, job.severity, job.top_n)
                        diagnostics = filtered_result.get("diagnostics", [])
                        
                        # Convert diagnostics to our format with line content
                        issues: List[Dict[str, Any]] = []
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
                        
                        # Create result with filtering metadata
                        total_diagnostics = len(json_data.get("generalDiagnostics", []))
                        job.result = {
                            "status": "success",
                            "summary": {
                                "total_issue_count": total_diagnostics,
                                "filtered_issue_count": len(issues),
                                "severity_filter": job.severity,
                                "top_n_limit": job.top_n
                            },
                            "issues": issues,
                        }
                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"[{job.job_type.value}:{job.id}] Failed to parse JSON output: {str(e)}"
                        )
                        # Fall back to treating output as plain text
                        job.result = {
                            "status": "success",
                            "summary": {
                                "total_issue_count": 1,
                                "filtered_issue_count": 1,
                                "severity_filter": job.severity,
                                "top_n_limit": job.top_n
                            },
                            "issues": [{
                                "line": 1,
                                "column": 1,
                                "message": f"Raw output: {basedpyright_output}",
                                "severity": "error",
                                "rule": None,
                                "line_content": None,
                            }],
                        }
                else:
                    # No output - create empty result
                    job.result = {
                        "status": "success",
                        "summary": {
                            "total_issue_count": 0,
                            "filtered_issue_count": 0,
                            "severity_filter": job.severity,
                            "top_n_limit": job.top_n
                        },
                        "issues": [],
                    }

                issue_count = job.result.get("summary", {}).get("filtered_issue_count", 0)
                logger.info(
                    f"[{job.job_type.value}:{job.id}] Analysis complete with {issue_count} issues"
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