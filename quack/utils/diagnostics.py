"""
Diagnostic processing utilities for basedpyright analysis.
"""

from typing import Dict, List, Any


def filter_and_output_json(data: Dict[str, Any], severity: str = "all", top_n: int = 10) -> Dict[str, Any]:
    """
    Filter diagnostics by severity and return the top N most critical errors as JSON.

    Args:
        data (dict): The raw output from basedpyright.
        severity (str): The severity level to filter by ("error", "warning", "info", or "all").
        top_n (int): The number of top critical errors to include in the output.

    Returns:
        dict: A JSON object containing the filtered and sorted diagnostics.
    """
    diagnostics = []
    for diag_dict in data.get("generalDiagnostics", []):
        diagnostics.append(diag_dict)

    # Sort by severity: 'error' comes before 'warning'
    severity_priority = {"error": 0, "warning": 1, "info": 2}
    diagnostics = sorted(
        diagnostics, key=lambda x: severity_priority.get(x.get("severity", "info"), 3)
    )
    
    # Filter by severity if not "all"
    if severity != "all":
        diagnostics = [
            diag for diag in diagnostics if diag.get("severity") == severity
        ]

    # Return the top N diagnostics as JSON
    return {"diagnostics": diagnostics[:top_n] if top_n is not None else diagnostics}