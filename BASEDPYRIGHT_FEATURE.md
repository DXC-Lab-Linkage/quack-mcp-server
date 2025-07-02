# Add BasedPyright Static Analysis Support

## Summary

This PR adds support for **basedpyright** static type analysis as an additional MCP tool alongside the existing mypy integration. BasedPyright provides faster type checking with enhanced features compared to standard pyright.

## Key Features

- **Automatic Installation**: Detects and installs basedpyright if not available
- **Configuration Detection**: Supports both `pyrightconfig.json` and `pyproject.toml` with verbose logging
- **Severity Filtering**: Filter results by error/warning/info severity levels  
- **Top-N Limiting**: Limit output to most critical issues
- **Robust Processing**: 3-retry mechanism with exponential backoff for reliability
- **Comprehensive Testing**: Full test coverage including edge cases and error handling

## Implementation

### Core Components
- `quack/processors/basedpyright.py` - Main processor implementation
- `tests/processors/test_basedpyright_processor.py` - Comprehensive test suite

### Key Capabilities
- Processes Python code through basedpyright with JSON output
- Integrates with existing diagnostic filtering utilities
- Handles installation, configuration detection, and error recovery
- Provides structured output with line content and metadata

## Testing

The implementation includes comprehensive tests covering:
- ✅ Successful analysis with type errors
- ✅ Clean code with no issues
- ✅ Error handling (stderr errors, timeouts, invalid JSON)
- ✅ Retry logic with exponential backoff
- ✅ Process failure scenarios

## Usage

BasedPyright analysis jobs can be processed through the existing job system, providing the same filtering and output format as other static analysis tools.