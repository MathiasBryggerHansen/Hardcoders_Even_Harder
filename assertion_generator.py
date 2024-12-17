# import ollama
# from typing import get_type_hints, List, Dict, Any
# import inspect
# import ast
# from typing import List, Dict, Any
# from pathlib import Path
# import json
# from hypothesis import given, strategies as st
# import pytest
#
#
# class QwenTestGenerator:
#     def __init__(self, parameters=None):
#         self.parameters = parameters or {
#             "temperature": 0.7,
#             "top_p": 0.8
#         }
#
#     def analyze_function(self, func) -> List[Dict[str, Any]]:
#         """Get test strategies from Qwen"""
#         source = inspect.getsource(func)
#         docstring = inspect.getdoc(func) or ""
#
#         messages = [{
#             "role": "system",
#             "content": """
# You are a test generator. Generate a JSON array of test strategies with these rules:
#
# 1. Format:
# - Valid JSON only: string error types ("ValueError"), "true"/"false", "null", quoted strings
# - Fields per test: "category" (boundary/edge/error/normal), "inputs" (parameters), "expected" (string for errors/number for calculations), "description" (purpose)
#
# 2. Coverage:
# - Boundary: limits/thresholds
# - Edge: extreme but valid
# - Error: invalid inputs
# - Normal: typical usage
# - Types, ranges, special values (0/-1/null), combinations
#
# 3. Quality:
# - Clear descriptions
# - No duplicates
# - Realistic values
#
# Return first a step-by-step plan, then output the JSON array in the format: ```json [...] ```."""
#         }, {
#             "role": "user",
#             "content": f"""Analyze this Python function and suggest test strategies:
#
#     Function:
#     {source}
#
#     Docstring:
#     {docstring}
#
#     Return a JSON array of test strategies, where each strategy has:
#     1. 'category': type of test (edge case, boundary, error, etc.)
#     2. 'inputs': example input values
#     3. 'expected': expected behavior or output
#     4. 'description': what the test verifies"""
#         }]
#
#         response = ollama.chat(
#             model="qwen2.5-coder",
#             messages=messages,
#             options=self.parameters
#         )
#
#         response_content = response['message']['content']
#         print(response_content)
#         try:
#             # Find content between ```json and ``` markers
#             json_start = response_content.find('```json\n') + 8  # len('```json\n')
#             json_end = response_content.find('\n```', json_start)
#
#             if json_start != -1 and json_end != -1:
#                 json_str = response_content[json_start:json_end].strip()
#                 strategies = json.loads(json_str)
#                 print(strategies)
#                 return strategies
#             else:
#                 print("No JSON code block found in response")
#                 return []
#         except (json.JSONDecodeError, KeyError) as e:
#             print(f"Failed to parse Qwen response: {e}")
#             return []
#
#     def generate_tests(self, func) -> str:
#         """Generate pytest test class from Qwen's strategy suggestions"""
#         strategies = self.analyze_function(func)
#
#         test_code = [
#             "import pytest",
#             "from hypothesis import given, strategies as st",
#             "",
#             f"class Test_{func.__name__}:",
#             f"    \"\"\"Tests for {func.__name__} generated with Qwen assistance\"\"\"",
#             ""
#         ]
#
#         # Add standard test cases
#         for i, strategy in enumerate(strategies):
#             if isinstance(strategy['expected'], str) and strategy['expected'].endswith('Error'):
#                 # Error test case
#                 test_code.extend([
#                     f"    def test_{strategy['category']}_{i}(self):",
#                     f"        \"\"\"Test: {strategy['description']}\"\"\"",
#                     f"        with pytest.raises({strategy['expected']}):",
#                     f"            {func.__name__}(**{strategy['inputs']})",
#                     ""
#                 ])
#             else:
#                 # Normal test case
#                 test_code.extend([
#                     f"    def test_{strategy['category']}_{i}(self):",
#                     f"        \"\"\"Test: {strategy['description']}\"\"\"",
#                     f"        result = {func.__name__}(**{strategy['inputs']})",
#                     f"        assert pytest.approx(result, rel=1e-2) == {strategy['expected']}",
#                     ""
#                 ])
#
#         # Add property-based tests
#         hints = get_type_hints(func)
#         if hints:
#             # Basic strategy mapping
#             strategy_map = {
#                 int: "integers()",
#                 float: "floats(allow_nan=False, allow_infinity=False)",
#                 bool: "booleans()",
#                 str: "text()",
#             }
#
#             params = []
#             for param, hint in hints.items():
#                 if param != 'return' and hint in strategy_map:
#                     params.append(f"{param}=st.{strategy_map[hint]}")
#
#             if params:
#                 test_code.extend([
#                     "    @given(",
#                     *[f"        {param}," for param in params],
#                     "    )",
#                     f"    def test_properties(self, {', '.join(p.split('=')[0] for p in params)}):",
#                     f"        result = {func.__name__}({', '.join(p.split('=')[0] for p in params)})",
#                     f"        assert isinstance(result, {hints.get('return', Any).__name__})",
#                     ""
#                 ])
#
#         return "\n".join(test_code)
#
#     def save_tests(self, func, output_path: Path = None):
#         """Generate and save tests"""
#         if output_path is None:
#             output_path = Path(f"test_{func.__name__}.py")
#
#         test_code = self.generate_tests(func)
#         output_path.write_text(test_code)
#         print(f"Generated tests saved to {output_path}")
#
#
# # Example usage
# if __name__ == "__main__":
#     def annotate_code_with_changes(code_string, changes_df):
#         """
#         Annotates code with lists of values that variables take and stdout content.
#
#         Args:
#             code_string (str): The original code as a string
#             changes_df (pd.DataFrame): DataFrame with _changed columns from get_variable_changes()
#         """
#         code_lines = code_string.split('\n')
#         annotated_lines = []
#
#         # Get variable columns (excluding metadata and _changed columns)
#         metadata_cols = {'timestamp', 'line', 'event', 'stdout', 'extra_info'}
#         var_cols = {col for col in changes_df.columns
#                     if not col.endswith('_changed')
#                     and col not in metadata_cols}
#
#         # Track when variables are first assigned
#         first_assignment = set()
#
#         # Process each line
#         for i, line in enumerate(code_lines):
#             current_line = line.rstrip()
#             next_line_data = changes_df[changes_df['line'] == i + 1]
#             current_line_data = changes_df[changes_df['line'] == i]
#
#             annotations = []
#
#             # Handle variable changes
#             if not next_line_data.empty:
#                 for var in var_cols:
#                     # Special case for function parameters (use current line)
#                     line_data = current_line_data if 'def' in line and var in line else next_line_data
#
#                     # Check if this is an initial assignment
#                     if '=' in line and var in line.split('=')[0] and var not in first_assignment:
#                         first_assignment.add(var)
#                         if f"{var}_changed" in changes_df.columns and line_data[f"{var}_changed"].any():
#                             values = [line_data[var].iloc[0]]  # Just take the first value
#                             if pd.notna(values[0]):
#                                 annotations.append(f"{var} = [{values[0]}]")
#                     # Regular variable change
#                     elif f"{var}_changed" in changes_df.columns and line_data[f"{var}_changed"].any():
#                         values = line_data[var].dropna().unique()
#                         if len(values) > 0 and var in line:
#                             annotations.append(f"{var} = [{', '.join(str(v) for v in values)}]")
#
#             # Add the current line with any variable annotations
#             if annotations:
#                 current_line += "  # " + ", ".join(annotations)
#             annotated_lines.append(current_line)
#
#             # Add stdout if print statement
#             stdout_data = changes_df[changes_df['line'] == i + 1]
#             if 'print' in line and changes_df['line'].eq(i - 1).any():
#                 stdout = changes_df[changes_df['line'].eq(i - 1)]['stdout'].iloc[0]
#                 if pd.notna(stdout):
#                     indent = len(line) - len(line.lstrip())
#                     cleaned_stdout = stdout.strip().replace('\n', '')
#                     stdout_line = ' ' * indent + f"# stdout: {cleaned_stdout}"
#                     annotated_lines.append(stdout_line)
#
#         return '\n'.join(annotated_lines)
#
#
#     generator = QwenTestGenerator()
#     #generator(calculate_discount())
#
#     generator.save_tests(annotate_code_with_changes)

import os
import tempfile
import subprocess
from pathlib import Path
import pytest
import sys
import importlib.util
import inspect
from typing import Tuple
import re


def extract_variable_values(test_module) -> dict:
    """Extract all variable values defined in the test module."""
    return {name: value for name, value in vars(test_module).items()
            if not name.startswith('__') and not callable(value)}


import os
import tempfile
import subprocess
from pathlib import Path
import pytest
import sys
import importlib.util
import inspect
from typing import Tuple


def run_pynguin_tests(code_string: str, module_name: str = "target_module") -> Tuple[str, bool]:
    """
    Generate tests with Pynguin and provide detailed assertion results.

    Args:
        code_string: The Python code to test
        module_name: Name for the module

    Returns:
        Tuple[str, bool]: (test results description, True if all tests passed)
    """
    os.environ["PYNGUIN_DANGER_AWARE"] = "true"
    all_tests_passed = True

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Write code to file
        module_path = temp_dir / f"{module_name}.py"
        with open(module_path, 'w') as f:
            f.write(code_string)

        cmd = [
            "pynguin",
            "--project-path", str(temp_dir),
            "--module-name", module_name,
            "--output-path", str(temp_dir),
            "--algorithm", "MOSA"
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)

            test_file = temp_dir / f"test_{module_name}.py"
            if not test_file.exists():
                return "No tests were generated.", False

            with open(test_file, 'r') as f:
                test_content = f.read()

            sys.path.insert(0, str(temp_dir))

            # Import test module
            test_spec = importlib.util.spec_from_file_location(f"test_{module_name}", test_file)
            test_module = importlib.util.module_from_spec(test_spec)
            test_spec.loader.exec_module(test_module)

            results = ["Test Results:\n"]

            # For each test case
            for name, obj in inspect.getmembers(test_module):
                if name.startswith('test_'):
                    results.append(f"Test: {name}")

                    # Get the test function source
                    test_src = inspect.getsource(obj)

                    try:
                        # Execute test
                        obj()

                        # Look for assertions in the source code
                        for line in test_src.split('\n'):
                            line = line.strip()
                            if 'assert' in line:
                                results.append(f"✓ PASSED: {line}")
                            elif 'pytest.raises' in line:
                                results.append(f"✓ PASSED: Expected exception was raised - {line}")

                    except AssertionError as e:
                        results.append(f"✗ FAILED: {str(e)}")
                        all_tests_passed = False
                    except Exception as e:
                        results.append(f"! ERROR: {type(e).__name__}: {str(e)}")
                        all_tests_passed = False

                    results.append("")

            sys.path.pop(0)

            return "\n".join(results), all_tests_passed

        except subprocess.CalledProcessError as e:
            return f"Error generating tests: {e.stderr.decode()}", False
        except Exception as e:
            return f"Error: {str(e)}", False


if __name__ == "__main__":
    # Example usage
    sample_code = """
def calculate_discount(price: float, discount_percent: float) -> float:
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")
    return price * (1 - discount_percent / 100)
    """

    results, success = run_pynguin_tests(sample_code)
    print(results)
    print(f"\nAll tests passed: {success}")