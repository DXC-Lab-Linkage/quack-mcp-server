"""
Test file for Quack MCP server.

This file contains intentional issues for testing linting and static analysis.
"""

# Linting issues
unused_var = 42  # Unused variable
x = 10  # Single-letter variable name

# Type issues
def add(a: int, b: int) -> int:
    return a + b

def greet(name: str) -> str:
    return "Hello, " + name

# Function with both linting and type issues
def calculate_average(numbers):  # Missing type annotations
    total = 0
    for num in numbers:
        total += num
    unused_result = total * 2  # Unused variable
    return total / len(numbers)

# Call with wrong type
result = add("5", 10)  # Type error: str + int

if __name__ == "__main__":
    print(greet("World"))
    print(calculate_average([1, 2, 3, 4, 5]))
