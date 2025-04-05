#!/bin/bash
# run_quack.sh - Wrapper script to run Quack MCP server with virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Default to stdio mode with debug flag
MODE="--debug"
HOST="0.0.0.0"
PORT="8000"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --sse)
      MODE="--debug --sse"
      shift
      ;;
    --host=*)
      HOST="${1#*=}"
      shift
      ;;
    --port=*)
      PORT="${1#*=}"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Run the Quack server with the specified mode
if [[ $MODE == *"--sse"* ]]; then
  echo "Starting Quack server with SSE transport on $HOST:$PORT"
  python "$SCRIPT_DIR/quack.py" $MODE --host="$HOST" --port="$PORT"
else
  echo "Starting Quack server with stdio transport"
  python "$SCRIPT_DIR/quack.py" $MODE
fi
