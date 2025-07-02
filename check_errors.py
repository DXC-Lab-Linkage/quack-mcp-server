import argparse
import json
import logging
import os
import subprocess
import sys

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Directories to check
SRC_DIR = os.getcwd()
TARGET_SUBDIRS = ["quack", "tests"]
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def is_basedpyright_installed():
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
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "basedpyright"], check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install basedpyright: {e}")
        sys.exit(1)


# Run basedpyright and get JSON output
def run_basedpyright(verbose=False):
    # Ensure basedpyright is installed
    if not is_basedpyright_installed():
        logger.info("basedpyright not found. Installing...")
        install_basedpyright()

    # Determine which config file takes precedence
    pyright_config = os.path.join(PROJECT_ROOT, "pyrightconfig.json")
    pyproject_toml = os.path.join(PROJECT_ROOT, "pyproject.toml")

    config_used = None
    if os.path.isfile(pyright_config):
        config_used = pyright_config
    elif os.path.isfile(pyproject_toml):
        config_used = pyproject_toml
    else:
        logger.debug("No configuration file found. Using default settings.")

    if config_used:
        logger.debug(f"Using configuration from: {config_used}")

    cmd = [
        "basedpyright",
        "--outputjson",
    ]
    for subdir in TARGET_SUBDIRS:
        cmd.append(os.path.join(SRC_DIR, subdir))
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode not in (0, 1):
        logger.error("Error running basedpyright:")
        logger.error(result.stderr.decode())
        return None

    return json.loads(result.stdout)


# Filter and sort errors
def process_diagnostics(data, severity="all"):
    diagnostics = []
    for diag_dict in data.get("generalDiagnostics", []):
        diagnostics.append(diag_dict)

    # Sort by severity: 'error' comes before 'warning'
    severity_priority = {"error": 0, "warning": 1, "info": 2}
    diagnostics = sorted(
        diagnostics, key=lambda x: severity_priority[x["severity"]]
    )
    if severity != "all":
        diagnostics = [
            diag for diag in diagnostics if diag["severity"] == severity
        ]

    return diagnostics


# Print top N most critical errors
def print_top_errors(diagnostics, top_n=10):
    logger.info(f"\n{'=' * 40}")
    logger.info("Top Critical Errors")
    logger.info(f"{'=' * 40}\n")
    output = "\n"
    for i, diag in enumerate(diagnostics[:top_n], 1):
        output += f"\n{i}. [{diag['severity'].upper()}] {diag['message']}\n"
        output += f"   File: {diag['file']}\n"
        if "range" in diag:
            start = diag["range"]["start"]
            end = diag["range"]["end"]
            output += f"   Location: L{start['line']} C{start['character']} - L{end['line']} C{end['character']}"
        output += "\n"
    logger.info(output)
    return output


# Main function
def main():
    parser = argparse.ArgumentParser(
        description="Run basedpyright with optional verbose logging."
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging."
    )
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.info("Running basedpyright...")
    result = run_basedpyright(args.verbose)

    if not result:
        return

    diagnostics = process_diagnostics(result, severity="error")
    error_count = sum(1 for d in diagnostics if d["severity"] == "error")

    logger.info(
        f"\nFound {len(diagnostics)} issues total ({error_count} errors, {len(diagnostics) - error_count} warnings)."
    )
    print_top_errors(diagnostics)


if __name__ == "__main__":
    main()
