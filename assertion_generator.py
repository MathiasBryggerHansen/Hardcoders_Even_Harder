import os
import sys
import pytest
from typing import Any
from pynguin.generator.generator import generate_tests


# ================ Example Functions to Test ================

def string_processor(text: str) -> str:
    """Capitalizes first letter of each word and removes extra spaces"""
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    words = text.split()
    return " ".join(word.capitalize() for word in words)


def number_transformer(num: float) -> float:
    """Applies a series of mathematical transformations"""
    if not isinstance(num, (int, float)):
        raise TypeError("Input must be a number")
    result = (num * 2 + 5) / 3
    return round(result, 2)


def list_manipulator(items: list) -> list:
    """Removes duplicates and sorts in reverse order"""
    if not isinstance(items, list):
        raise TypeError("Input must be a list")
    return sorted(list(set(items)), reverse=True)


def dict_validator(data: dict) -> bool:
    """Checks if dictionary has required structure"""
    if not isinstance(data, dict):
        raise TypeError("Input must be a dictionary")
    required_keys = {'name', 'age', 'active'}
    return all(key in data for key in required_keys)


# ================ Test Generation Code ================

def write_temp_module():
    """Write the functions to a temporary module file for Pynguin to analyze"""
    with open("temp_module.py", "w") as f:
        f.write("""
def string_processor(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    words = text.split()
    return " ".join(word.capitalize() for word in words)

def number_transformer(num: float) -> float:
    if not isinstance(num, (int, float)):
        raise TypeError("Input must be a number")
    result = (num * 2 + 5) / 3
    return round(result, 2)

def list_manipulator(items: list) -> list:
    if not isinstance(items, list):
        raise TypeError("Input must be a list")
    return sorted(list(set(items)), reverse=True)

def dict_validator(data: dict) -> bool:
    if not isinstance(data, dict):
        raise TypeError("Input must be a dictionary")
    required_keys = {'name', 'age', 'active'}
    return all(key in data for key in required_keys)
""")


def generate_and_run_tests():
    """Generate and execute tests using Pynguin"""
    # Create temporary module
    write_temp_module()

    # Ensure output directory exists
    os.makedirs("generated_tests", exist_ok=True)

    # Generate tests using Pynguin
    config = {
        "project_path": os.path.dirname(os.path.abspath(__file__)),
        "module_name": "temp_module",
        "output_path": "generated_tests",
        "assertion_generation": True,
        "algorithm": "DYNAMOSA",
        "budget": 30,
        "max_length": 10
    }

    try:
        result = generate_tests(**config)
        print(f"Test generation completed with result: {result}")

        # Run the generated tests
        pytest.main(["generated_tests"])

    except Exception as e:
        print(f"Error during test generation: {e}")
    finally:
        # Cleanup temporary module
        if os.path.exists("temp_module.py"):
            os.remove("temp_module.py")


if __name__ == "__main__":
    # Example usage of the functions
    print("Testing functions manually:")

    # String processor test
    text_result = string_processor("hello   world  python")
    print(f"String processor: {text_result}")

    # Number transformer test
    num_result = number_transformer(10)
    print(f"Number transformer: {num_result}")

    # List manipulator test
    list_result = list_manipulator([1, 3, 2, 3, 1, 4])
    print(f"List manipulator: {list_result}")

    # Dict validator test
    dict_result = dict_validator({"name": "John", "age": 30, "active": True})
    print(f"Dict validator: {dict_result}")

    print("\nGenerating and running automated tests...")
    generate_and_run_tests()