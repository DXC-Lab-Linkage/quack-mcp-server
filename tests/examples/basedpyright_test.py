"""
Test file for basedpyright static analysis.

This file contains intentional errors that basedpyright should detect.
"""

from typing import List, Dict, Optional, Union
import os


# Type annotation errors
def process_data(data):  # Missing type annotations
    return data * 2


def get_user_info(user_id: int) -> Dict[str, str]:
    # Return type mismatch - returning int instead of str values
    return {"name": "John", "age": 25}  # age should be str according to annotation


# None/Optional handling issues
def get_config(key: str) -> str:
    config = {"debug": "true", "port": "8080"}
    return config.get(key)  # Returns Optional[str] but function expects str


def process_optional_value(value: Optional[str]) -> str:
    # Potential None access without check
    return value.upper()  # value could be None


# List/Dict access issues
def get_first_item(items: List[str]) -> str:
    return items[0]  # Could raise IndexError if list is empty


def access_dict_key(data: Dict[str, int], key: str) -> int:
    return data[key]  # Could raise KeyError if key doesn't exist


# Union type issues
def handle_number(value: Union[int, str]) -> int:
    return value * 2  # Can't multiply str by int


# Attribute access on potentially None values
class User:
    def __init__(self, name: str):
        self.name = name
        self.email: Optional[str] = None


def get_email_domain(user: User) -> str:
    # Potential None access
    return user.email.split("@")[1]  # user.email could be None


# Unused imports and variables
import json  # Unused import
import sys   # Unused import

unused_variable = "This is never used"


# Unreachable code
def unreachable_example():
    return "early return"
    print("This will never execute")  # Unreachable code


# Inconsistent return types
def inconsistent_return(condition: bool):
    if condition:
        return "string"
    else:
        return 42  # Different return type


# Missing return statement
def missing_return(x: int) -> str:
    if x > 0:
        return "positive"
    # Missing return for x <= 0 case


# Redefined variables
def redefined_vars():
    result = "initial"
    result = 123  # Type change
    return result


# Assignment to constant-like variables
PI = 3.14159
PI = 2.71828  # Reassigning what looks like a constant


if __name__ == "__main__":
    # Examples that would trigger runtime errors
    print(process_data("test"))
    print(get_user_info(1))
    print(get_config("missing_key"))
    
    user = User("John")
    print(get_email_domain(user))  # Will fail at runtime