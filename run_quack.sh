#!/bin/bash
# run_quack.sh - Wrapper script to run Quack MCP server with virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Run the Quack server with debug flag
python "$SCRIPT_DIR/quack.py" --debug
