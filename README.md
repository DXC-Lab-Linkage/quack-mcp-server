# Quack MCP Server

Quack is a continuous integration server built as an MCP server that automates code analysis and testing for Python code. It provides tools for linting and static type analysis of Python code.

## Features

- **Linting**: Analyzes Python code for style, formatting, and code quality issues using pylint.
- **Static Analysis**: Performs static type checking using mypy to identify type errors.
- **Asynchronous Processing**: Jobs are processed asynchronously, allowing for concurrent analysis of multiple code submissions.
- **Job Management**: Track and retrieve results of submitted jobs.

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/quack.git
cd quack
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

The Quack server requires the following dependencies:
```
mcp[cli]
pylint
mypy
pytest
pytest-asyncio
```

## Usage

### Starting the Server

To start the Quack server:

```bash
python3 quack.py
```

For debug logging:

```bash
python3 quack.py --debug
```

Alternatively, you can use the provided shell script:

```bash
./run_quack.sh
```

### Using the MCP Tools

Quack exposes the following MCP tools:

1. `submit_code`: Submit code for both linting and static analysis.
2. `submit_code_for_linting`: Submit code for linting only.
3. `submit_code_for_static_analysis`: Submit code for static analysis only.
4. `get_job_results`: Get the results of a submitted job.
5. `list_jobs`: List all jobs and their status.

## Testing Architecture

Quack has two distinct testing concepts:

1. **Tests OF Quack**: The tests in the `tests/` directory verify that the Quack server, job manager, and processors are working correctly. When you add a new processor, you should add tests here to verify your processor works.

2. **Tests BY Quack**: These are the analyses that Quack performs on submitted code. The lint processor and static analysis processor analyze Python code for issues. Your new processor will do the same on separate code submissions.

### Directory Structure

```
tests/
  ├── server/          # Tests OF the server functionality
  │   ├── test_server_direct.py    # Direct testing of job manager
  │   ├── test_server_auto.py      # Auto-starts and stops the server
  │   └── test_server_client.py    # Tests the MCP client interface
  ├── processors/      # Tests OF the processors
  │   ├── test_lint_processor.py        # Tests for lint processor
  │   └── test_static_analysis_processor.py  # Tests for static analysis
  └── examples/        # Example submissions for testing BY the server
      └── example_code.py          # Contains intentional issues for testing
```

When implementing a new processor (e.g., a test coverage processor):
1. Create your processor in `quack/processors/`
2. Add tests for your processor in `tests/processors/`
3. Use code in `tests/examples/` to test what your processor analyzes

### Running Tests

The repository includes a comprehensive test suite in the `tests` directory. All tests are managed using pytest.

1. Run all tests:

```bash
python -m pytest tests/ --asyncio-mode=auto
```

2. Run a specific test file:

```bash
python -m pytest tests/server/test_server_direct.py -v --asyncio-mode=auto
```

3. Run tests for a specific processor:

```bash
python -m pytest tests/processors/test_lint_processor.py -v
```

4. Run tests with verbose output and show test progress:

```bash
python -m pytest tests/ -v --asyncio-mode=auto
```

5. Run tests and stop on the first failure:

```bash
python -m pytest tests/ -x --asyncio-mode=auto
```

#### Automatic Server Management

Many of the tests automatically start and stop the Quack server as needed, so you don't need to manually manage the server process during testing. This is handled by pytest fixtures in the `conftest.py` file.

The server tests in `tests/server/test_server_auto.py` demonstrate how to automatically start and stop the server for testing. These tests verify that:
1. The server starts up correctly
2. The server can process jobs
3. The server shuts down properly

## Setting Up Quack with Cline

Quack can be integrated with Cline to provide code analysis capabilities directly through the Cline interface.

### Configuration Steps

1. Configure Cline MCP Settings

   The Quack server can be configured in Cline's MCP settings file at:
   ```
   ~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
   ```

   With the following configuration:
   ```json
   {
     "mcpServers": {
       "quack": {
         "command": "python3",
         "args": ["/path/to/your/quack.py", "--debug"],
         "env": {},
         "disabled": false,
         "autoApprove": []
       }
     }
   }
   ```

### Using Quack with Cline

Once configured, you can use Cline to analyze Python code using the Quack server. Here are some example prompts:

- **Analyze code for linting issues**:
  ```
  Analyze this Python code for linting issues:
  [paste your code here]
  ```

- **Check code for type errors**:
  ```
  Check this Python code for type errors:
  [paste your code here]
  ```

- **Get comprehensive feedback**:
  ```
  What's wrong with this Python function?
  [paste your function here]
  ```

### Sample Code for Testing

You can use the following sample code with intentional issues to test the Quack server:

```python
# Linting issues
unused_var = 42  # Unused variable
x = 10  # Single-letter variable name

# Type issues
def add(a: int, b: int) -> int:
    return a + b

# Function with both linting and type issues
def calculate_average(numbers):  # Missing type annotations
    total = 0
    for num in numbers:
        total += num
    unused_result = total * 2  # Unused variable
    return total / len(numbers)

# Call with wrong type
result = add("5", 10)  # Type error: str + int
```

### How It Works

1. When you ask Cline to analyze Python code, Cline will use the Quack MCP server
2. The Quack server will process the code through its linting and static analysis tools
3. The results will be returned to Cline, which will present them to you in a readable format

### Troubleshooting

If Cline doesn't seem to be using the Quack server:

1. Make sure the Quack server is properly configured in the MCP settings file
2. Check that the path to the quack.py file is correct
3. Ensure all dependencies are installed
4. Restart VSCode to reload the MCP settings

## Architecture

Quack is built using the Model Context Protocol (MCP) and consists of the following components:

- **Server**: The main MCP server that handles client connections and tool invocations.
- **Job Manager**: Manages the lifecycle of jobs, including submission, processing, and result retrieval.
- **Processors**: Specialized components that perform the actual code analysis:
  - **Lint Processor**: Uses pylint to analyze code style and quality.
  - **Static Analysis Processor**: Uses mypy to perform static type checking.

## Development

### Adding New Processors

To add a new processor:

1. Create a new processor class in the `quack/processors` directory.
2. Implement the `process` method to perform the analysis.
3. Register the processor in the server.
4. Add tests for your processor in `tests/processors/`.

#### Example: Adding a Test Coverage Processor

1. Create `quack/processors/coverage.py` with your processor implementation
2. Add the processor to the server in `quack/server.py`
3. Create tests in `tests/processors/test_coverage_processor.py`
4. Test your processor with example code in `tests/examples/`

### Debugging

Run the server with the `--debug` flag to enable detailed logging:

```bash
python3 quack.py --debug
```

Logs are written to both the console and `logs/quack.log`.

## License

[MIT License](LICENSE)
