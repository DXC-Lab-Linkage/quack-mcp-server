import json
import os
import subprocess
import sys

# Directories to check
SRC_DIR = os.getcwd()
TARGET_SUBDIRS = ["quack", "tests"]


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
        print(f"Failed to install basedpyright: {e}")
        sys.exit(1)


# Run basedpyright and get JSON output
def run_basedpyright():
    # Check if basedpyright is available
    if not is_basedpyright_installed():
        print("basedpyright not found. Installing...")
        install_basedpyright()

    cmd = [
        "basedpyright",
        "--outputjson",
    ]
    for subdir in TARGET_SUBDIRS:
        cmd.append(os.path.join(SRC_DIR, subdir))
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0 and result.returncode != 1:
        print("Error running basedpyright:")
        print(result.stderr.decode())
        return None

    return json.loads(result.stdout)


# Filter and sort errors
def process_diagnostics(data):
    diagnostics = []
    for diag_dict in data.get("generalDiagnostics", []):
        diagnostics.append(diag_dict)

    # Sort by severity: 'error' comes before 'warning'
    severity_priority = {"error": 0, "warning": 1, "info": 2}
    diagnostics = sorted(
        diagnostics, key=lambda x: severity_priority[x["severity"]]
    )

    return diagnostics


# Print top N most critical errors
def print_top_errors(diagnostics, severity="error", top_n=10):
    print(f"\n{'=' * 40}")
    print("Top Critical Errors")
    print(f"{'=' * 40}\n")

    for i, diag in enumerate(diagnostics[:top_n], 1):
        print(f"{i}. [{diag['severity'].upper()}] {diag['message']}")
        print(f"   File: {diag['file']}")
        if "range" in diag:
            start = diag["range"]["start"]
            end = diag["range"]["end"]
            print(
                f"   Location: L{start['line']} C{start['character']} - L{end['line']} C{end['character']}"
            )
        print()


# Main function
def main():
    print("Running basedpyright...")
    result = run_basedpyright()

    if not result:
        return

    diagnostics = process_diagnostics(result)
    error_count = sum(1 for d in diagnostics if d["severity"] == "error")

    print(
        f"\nFound {len(diagnostics)} issues total ({error_count} errors, {len(diagnostics) - error_count} warnings)."
    )
    print_top_errors(diagnostics)


if __name__ == "__main__":
    main()
