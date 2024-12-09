import os
import re
import sys
import tempfile
import subprocess
import venv
import ollama
from typing import Optional, List, Tuple, Union, Set
from datetime import datetime
from collections import deque
from dataclasses import dataclass
from difflib import unified_diff
from error_handler import enhance_error, BaseErrorHandler, WebAppErrorHandler
from static_analysis import EnhancedErrorHandler
from typing import Optional, Tuple
import itertools


@dataclass
class AttemptHistory:
    code: str
    error: str
    timestamp: datetime
    diff_from_previous: Optional[str] = None
    error_analysis: Optional[str] = None
    stdout: Optional[str] = None


class CodeEvolutionHandler:
    def __init__(self, history_size: int = 5):
        self.history = deque(maxlen=history_size)
        self.project_dir = None
        self.venv_path = None
        self.installed_packages: Set[str] = set()
        self.error_handler = EnhancedErrorHandler()
        self.create_sandbox_environment()
        self.parameters = {'temperature': 1, 'top_p': 0.9, 'top_k': 50}

    def generate_code_diff(self, old_code: str, new_code: str) -> str:
        """Generate a readable diff focusing on code movements and changes."""

        def normalize_code(code: str) -> list[str]:
            lines = [line.rstrip() for line in code.splitlines()]
            while lines and not lines[0].strip():
                lines.pop(0)
            while lines and not lines[-1].strip():
                lines.pop()

            normalized = []
            for line in lines:
                if line.strip():
                    if "print" in line:
                        continue
                    indent = len(line) - len(line.lstrip())
                    cleaned = ' '.join(line.replace('\t', '    ').split())
                    normalized.append(' ' * indent + cleaned)
                else:
                    normalized.append('')
            return normalized

        def detect_block_movement(old_lines: list[str], new_lines: list[str],
                                  start_old: int, start_new: int) -> tuple[int, int]:
            """Detect if a block of code was moved."""
            max_block = 0
            block_start = None

            for i in range(start_old, len(old_lines)):
                for j in range(start_new, len(new_lines)):
                    k = 0
                    while (i + k < len(old_lines) and j + k < len(new_lines)
                           and old_lines[i + k] == new_lines[j + k]):
                        k += 1
                    if k > max_block:
                        max_block = k
                        block_start = (i, j)

            return block_start if max_block > 2 else None

        old_lines = normalize_code(old_code)
        new_lines = normalize_code(new_code)

        changes = []
        i = j = 0

        while i < len(old_lines) or j < len(new_lines):
            movement = detect_block_movement(old_lines, new_lines, i, j)

            if movement:
                old_pos, new_pos = movement
                if old_pos != i or new_pos != j:
                    changes.append(f"\nCode moved from line {i} to {new_pos}:")
                    block = []
                    while i < old_pos:
                        if i < len(old_lines):
                            block.append(f"Removed: {old_lines[i]}")
                        i += 1
                    while j < new_pos:
                        if j < len(new_lines):
                            block.append(f"Added:   {new_lines[j]}")
                        j += 1
                    changes.extend(block)

                while i < len(old_lines) and j < len(new_lines) and old_lines[i] == new_lines[j]:
                    changes.append(f"Context: {old_lines[i]}")
                    i += 1
                    j += 1
            else:
                if i < len(old_lines):
                    changes.append(f"Removed: {old_lines[i]}")
                    i += 1
                if j < len(new_lines):
                    changes.append(f"Added:   {new_lines[j]}")
                    j += 1

        return '\n'.join(changes)

    def filter_lines(self, text, ignore_keyword):
        """Filter out lines containing the ignore keyword."""
        lines = text.strip().splitlines()
        return [line for line in lines if ignore_keyword not in line]

    def create_sandbox_environment(self):
        """Create an isolated virtual environment for code execution."""
        self.project_dir = tempfile.mkdtemp()

        self.venv_path = os.path.join(self.project_dir, 'venv')

        # Clear any previously installed packages
        self.installed_packages.clear()

        try:
            venv.create(self.venv_path, with_pip=True)

            # Verify pip exists
            pip_path = os.path.join(self.venv_path, 'Scripts', 'pip.exe') if os.name == 'nt' \
                else os.path.join(self.venv_path, 'bin', 'pip')

            if not os.path.exists(pip_path):
                raise RuntimeError(f"Pip not found at {pip_path}")

            # Test pip installation
            test_result = subprocess.run(
                [pip_path, '--version'],
                capture_output=True,
                text=True
            )
            if test_result.returncode != 0:
                raise RuntimeError(f"Pip test failed: {test_result.stderr}")

        except Exception as e:
            self.cleanup()
            raise

    def cleanup(self):
        """Clean up the environment."""
        if self.project_dir and os.path.exists(self.project_dir):
            try:
                import shutil
                shutil.rmtree(self.project_dir)
                self.project_dir = None
                self.venv_path = None
                self.installed_packages.clear()
            except Exception as e:
                print(f"Error cleaning up environment: {e}")

    def _combine_code(self, code_string: str, max_attempts: int = 5) -> Optional[str]:
        """Process and combine code using Ollama with proper message handling and testing.

        Args:
            code_string (str): The code snippets to combine
            max_attempts (int): Maximum number of attempts to generate valid code

        Returns:
            Optional[str]: The successfully combined and tested code, or None if all attempts fail
        """
        base_system_message = {
            'role': 'system',
            'content': (
                "You are designed to generate a fully functional python app that adheres to all requirements "
                "given separate code snippets. You will receive detailed error analysis and patterns to help "
                "improve each iteration of the code."
            )
        }

        base_user_message = {
            'role': 'user',
            'content': (
                    "You must convert this Python code according to these EXACT requirements:\n"
                    "1. It needs to be a combined functional python app with ***ALL*** functions included!\n"
                    "2. Include all needed imports\n"
                    "3. Remove ALL test code, print statements, and debugging code\n"
                    "4. Remove ALL dummy and example functions\n"
                    "5. Keep only the core functional code\n"
                    "6. No testing or dummy example functions\n"
                    "7. The code is within ```python ``` tags\n"
                    "8. ***OUTPUT THE FULL PYTHON APP***.\n"
                    "Here are the code snippets:\n\n"
                    + code_string
            )
        }

        self.error_handler.reset_tracking()

        for attempt in range(max_attempts):
            try:
                print(f"\nCombine code attempt {attempt + 1}/{max_attempts}")

                messages = [base_system_message]

                # Enhance the prompt with error analysis if we have previous attempts
                if attempt > 0 and hasattr(self, 'history') and self.history:
                    last_attempt = self.history[-1]

                    # Create detailed error context for the LLM
                    error_context = (
                        "Add informative prints WITHIN code.\n "
                        "ERRORS and WARNINGS from previous analysis is commented in the code.\n"
                        "Previous attempt analysis:\n"
                        f"1. Code Issues:\n{last_attempt.error_analysis or 'None'}\n\n"
                        f"2. Runtime Behavior:\n{last_attempt.error}\n\n"
                        f"3. Previous code:\n{last_attempt.code}\n\n"
                    )

                    # Add error pattern information if available
                    if hasattr(self.error_handler, 'error_count'):
                        recurring_errors = [
                            f"- {error}: occurred {count} times"
                            for error, count in self.error_handler.error_count.items()
                            if count > 1
                        ]
                        if recurring_errors:
                            error_context += (
                                    "\nRecurring error patterns to specifically address:\n" +
                                    "\n".join(recurring_errors)
                            )

                    messages.append({
                        'role': 'system',
                        'content': error_context
                    })

                messages.append(base_user_message)

                # Generate combined code
                response = ollama.chat(
                    model="qwen2.5-coder",
                    messages=messages,
                    options=self.parameters
                )

                if not response or not isinstance(response, dict):
                    raise RuntimeError(f"Unexpected response format: {response}")

                if 'message' not in response or 'content' not in response['message']:
                    raise RuntimeError(f"Response missing required fields: {response}")

                combined_code = self.extract_code(response)
                if not combined_code or not combined_code.strip():
                    raise ValueError("Generated empty code")

                combined_code = self.clean_main_block(combined_code)

                # Analyze and test the code
                analysis_results = self.error_handler.analyze_code(combined_code)
                if analysis_results and isinstance(analysis_results, dict):
                    if analysis_results.get('pylint_errors') or analysis_results.get('bandit_issues'):
                        raise RuntimeError("Static analysis found issues")

                requirements = self.extract_requirements(combined_code)
                ret_code, stdout, stderr = self.install_requirements(requirements)
                if ret_code != 0:
                    raise RuntimeError(f"Requirements installation failed: {stderr}")

                ret_code, stdout, stderr = self.execute_code(combined_code)
                if ret_code != 0:
                    raise RuntimeError(f"Code execution failed: {stderr}")

                self.add_attempt(combined_code, "Success - no errors", stdout)
                return combined_code

            except Exception as e:
                code_to_analyze = combined_code if 'combined_code' in locals() else code_string
                enhanced_error = self.error_handler.enhance_error(e, code_to_analyze)

                self.add_attempt(
                    code_to_analyze,
                    enhanced_error,
                    stdout if 'stdout' in locals() else None
                )

                self.get_next_parameters()

                if attempt == max_attempts - 1:
                    return None

        return None

    def extract_code(self, response: Union[str, dict]) -> str:
        """Extract and clean code blocks from LLM response, preserving all functions.

        Args:
            response (Union[str, dict]): The LLM response, either as a string or a dictionary

        Returns:
            str: The cleaned and formatted code with all functions preserved
        """
        # Get response text
        if isinstance(response, dict):
            if 'message' in response and 'content' in response['message']:
                response_text = response['message']['content']
            else:
                raise ValueError(f"Unexpected response format: {response}")
        else:
            response_text = response

        # Extract all code blocks
        all_code = []

        # Try ```python blocks first
        if '```python' in response_text:
            parts = response_text.split('```python')
            for part in parts[1:]:  # Skip the first part before ```python
                if '```' in part:
                    code_block = part.split('```')[0].strip()
                    if code_block:
                        all_code.append(code_block)
        # If no ```python blocks, try regular ``` blocks
        elif '```' in response_text:
            parts = response_text.split('```')
            # Take the content between ``` markers (odd-numbered parts)
            code_blocks = parts[1::2]
            all_code.extend(block.strip() for block in code_blocks if block.strip())

        if not all_code:
            return response_text.strip()

        # Process all code blocks to collect imports and functions
        import_lines = set()
        function_blocks = []

        for block in all_code:
            block_lines = block.split('\n')
            block_imports = []
            block_functions = []
            current_function = []

            for line in block_lines:
                stripped = line.strip()
                # Collect imports
                if stripped.startswith(('import ', 'from ')):
                    block_imports.append(line)
                # Collect function blocks
                elif stripped.startswith('def '):
                    if current_function:  # Save any previous function
                        function_blocks.append('\n'.join(current_function))
                    current_function = [line]
                elif current_function:
                    current_function.append(line)
                elif stripped and not stripped.startswith('#'):
                    block_functions.append(line)

            if current_function:  # Save last function
                function_blocks.append('\n'.join(current_function))
            if block_functions:  # Save any non-function code
                function_blocks.append('\n'.join(block_functions))

            import_lines.update(block_imports)

        # Combine everything with proper spacing
        final_code = []

        # Add imports at the top
        if import_lines:
            final_code.extend(sorted(import_lines))
            final_code.append('')  # Empty line after imports

        # Add all function implementations
        final_code.extend(function_blocks)

        # Clean up extra blank lines
        result = '\n'.join(final_code)
        result = '\n'.join(line for line, _ in itertools.groupby(result.splitlines()))

        return result

    def extract_requirements(self, code: str) -> List[str]:
        print('Extracting requirements...')
        """Extract pip install requirements from imports."""
        import sys
        # List of common built-in modules
        stdlib_modules = set([
            'time', 'json', 're', 'os', 'sys', 'datetime', 'collections',
            'math', 'random', 'itertools', 'functools', 'typing', 'tempfile',
            'subprocess', 'shutil', 'pathlib', 'logging', 'abc', 'copy',
            'string', 'enum', 'uuid'
        ])

        if hasattr(sys, 'stdlib_module_names'):
            stdlib_modules.update(sys.stdlib_module_names)

        requirements = set()
        lines = code.split('\n')

        for line in lines:
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                module = line.split()[1].split('.')[0]
                # Only add if not a built-in module
                if module not in stdlib_modules:
                    requirements.add(module)
        return list(requirements)

    def clean_main_block(self, code: str) -> str:
        """Remove if __name__ == '__main__' block and any test code from the generated code."""
        if not code:
            return ""

        lines = code.splitlines()
        cleaned_lines = []
        in_main_block = False

        for line in lines:
            # Check for main block start
            if line.strip().startswith('if __name__ == '):
                in_main_block = True
                continue

            # Skip lines while in main block until we hit an unindented line
            if in_main_block:
                if line.strip() and not line.startswith((' ', '\t')):
                    in_main_block = False
                else:
                    continue

            # Add non-main-block lines
            cleaned_lines.append(line)

        # Remove any trailing empty lines
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()

        return '\n'.join(cleaned_lines)

    def install_requirements(self, requirements: List[str]) -> Tuple[int, str, str]:
        print("Installing requirements...")
        """Install requirements in the isolated environment."""
        if not requirements:
            return 0, "No requirements to install", ""

        new_requirements = [req for req in requirements
                            if req not in self.installed_packages]

        if not new_requirements:
            return 0, "All packages already installed", ""

        pip_path = os.path.join(self.venv_path, 'Scripts', 'pip.exe') if os.name == 'nt' \
            else os.path.join(self.venv_path, 'bin', 'pip')

        try:
            print("updating pip")
            # Try upgrading pip first
            subprocess.run(
                [pip_path, 'install', '--upgrade', 'pip'],
                capture_output=True,
                text=True
            )

            # Install with verbose output
            result = subprocess.run(
                [pip_path, 'install', '-v'] + new_requirements,
                capture_output=True,
                text=True
            )

            print(f"Pip stdout: {result.stdout}")  # Debug output

            if result.returncode == 0:
                self.installed_packages.update(new_requirements)

            return result.returncode, result.stdout, result.stderr

        except Exception as e:
            print(f"Exception during pip install: {str(e)}")  # Debug exception
            return 1, "", str(e)

    def execute_code(self, code: str) -> Tuple[int, str, str]:
        """Execute code in the isolated environment."""
        temp_file_path = None
        try:
            # Try to compile the code first to catch syntax errors
            try:
                compile(code, '<string>', 'exec')
            except Exception as e:
                error = self.error_handler.enhance_error(e, code)
                return 1, "", error

            with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.py',
                    delete=False
            ) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name

            python_path = os.path.join(self.venv_path, 'Scripts', 'python.exe') if os.name == 'nt' \
                else os.path.join(self.venv_path, 'bin', 'python')

            # Add print statement to see what's happening
            wrapped_code = code
            with open(temp_file_path, 'w') as f:
                f.write(wrapped_code)

            result = subprocess.run(
                [python_path, temp_file_path],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                with open(temp_file_path, 'r') as f:
                    executed_code = f.read()
                # executed_code = self.remove_print_calls(executed_code)
                with open(temp_file_path, 'w') as f:
                    f.write(executed_code)

            if result.returncode != 0:
                error = self.error_handler.enhance_error(RuntimeError(result.stderr), code)
                return 1, result.stdout, error

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            error = self.error_handler.enhance_error(
                TimeoutError("Code execution took too long - check for infinite loops or blocking operations"), code
            )
            return 1, "", error
        except Exception as e:
            error = self.error_handler.enhance_error(e, code)
            return 1, "", error
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    print(f"Warning: Failed to clean up temporary file: {e}")

    def get_next_parameters(self) -> None:
        """Update model parameters based on error patterns."""
        if not hasattr(self.error_handler, 'error_count'):
            print("Error handler missing error_count attribute")
            return

        error_counts = self.error_handler.error_count
        if not error_counts:
            return

        # Calculate adjustments based on the highest error count
        max_error_count = max(error_counts.values())

        if max_error_count > 1:
            self.parameters['top_p'] = min(0.98, 0.9 + 0.01 * (max_error_count - 1))
            self.parameters['temperature'] = min(2, 1 + 0.2 * (max_error_count - 1))
            self.parameters['top_k'] = min(50 + max_error_count * 10, 100)

            print(f"Current error counts: {error_counts}")
            print(f"Adjusting parameters based on max error count {max_error_count}:")
            print(f"  - top_p: {self.parameters['top_p']}")
            print(f"  - temperature: {self.parameters['temperature']}")
            print(f"  - top_k: {self.parameters['top_k']}")

    #def add_attempt(self, code: str, error: str, stdout: Optional[str] = None, parameters: Optional[dict] = None):
        #"""Record a code execution attempt with enhanced error information."""
        # diff = None
        # if self.history:
        #     diff = self.generate_code_diff(
        #         self.history[-1].code,
        #         code,
        #     )

        # error_analysis = None
        # if hasattr(self.error_handler, 'static_analysis_results'):
        #     if self.error_handler.static_analysis_results:
        #         error_analysis = "\n".join([
        #             "Static Analysis Findings:",
        #             *[f"- {pattern}" for pattern in
        #               self.error_handler.static_analysis_results['error_patterns']]
        #         ])

    def add_attempt(self, code: str, error: str, stdout: Optional[str] = None, parameters: Optional[dict] = None):
        """Record a code execution attempt with enhanced error information."""
        self.history.append(AttemptHistory(
            code=code,
            error=error,
            timestamp=datetime.now(),
            stdout=stdout
        ))

    @dataclass
    class AttemptHistory:
        code: str
        error: str
        timestamp: datetime
        diff_from_previous: Optional[str] = None
        error_analysis: Optional[str] = None
        stdout: Optional[str] = None
        parameters: Optional[dict] = None

    def build_chat_prompt(self, code_requirements: str, attempt: int) -> str:
        """Build the chat prompt based on attempt number and any recurring error patterns."""
        messages = [{
            'role': 'system',
            'content': "You are designed to generate exact python code that adheres to all requirements."
        }]
        # Check if we have recurring errors to inform the system message
        if attempt > 0 and self.history and hasattr(self.error_handler, 'error_count'):
            last_error = self.history[-1].error
            for error_key, count in self.error_handler.error_count.items():
                if count > 1:
                    messages.append({
                        'role': 'system',
                        'content': f"Warning: You have made the same type of error {count} times. "
                                   f"The previous approaches have not resolved: {error_key}. "
                                   "You must take a fundamentally different approach to this section of code."
                    })

        # Add the main instruction message
        user_message = f"Code requirement: {code_requirements}\n"
        if attempt == 0:
            user_message += "First plan out step-by-step what needs to be done to write the function.\n"
        elif attempt > 0 and self.history:
            last_attempt = self.history[-1]
            history_info = "The ***GOAL*** is to: ***PASS all errors and warnings*** that occurred in the previous attempt.\n"
            output_info = f"\ndebug print output:\n{last_attempt.stdout}" if last_attempt.stdout else ""

            if attempt == 1:
                history_info += (f"Previous attempt:\n```python\n{last_attempt.code}\n```\n"
                                 f"Error: {last_attempt.error}\n"
                                 f"Error analysis: {last_attempt.error_analysis or 'None'}"
                                 f"{output_info}")
            else:
                history_info += (f"Previous attempt:\n```python\n{last_attempt.code}\n```\n"
                                 f"Last attempt error: {last_attempt.error}\n"
                                 f"{output_info}")

            user_message += f"\nAttempt {attempt + 1}\n{history_info}\n"
            user_message += "Change the code, particularly the code shown after 'Code:' to !!***FIX ALL WARNINGS AND ERRORS LISTED***!!. \n"
            user_message += "ADD prints for debugging purposes and ADD test code."

        user_message += "\nEnclose code in ```python ``` tags. \n"

        messages.append({
            'role': 'user',
            'content': user_message
        })

        return messages

    def reset_parameters(self) -> None:
        """Reset model parameters to their default values."""
        self.parameters = {
            'temperature': 1,
            'top_p': 0.9,
            'top_k': 50
        }

    def process_with_reflection(self, code_requirements: list, max_attempts: int = 20) -> Optional[str]:
        """Process code requirements with multiple attempts and enhanced error handling.

        Args:
            code_requirements (list): List of code requirements to implement
            max_attempts (int): Maximum number of attempts per requirement

        Returns:
            Optional[str]: The successfully combined and tested code, or None if attempts fail
        """
        if not code_requirements:
            raise ValueError("Code requirements list cannot be empty")

        try:
            combined_code = ""

            for requirement_index, func in enumerate(code_requirements):
                if not isinstance(func, str) or not func.strip():
                    raise ValueError(f"Invalid requirement at index {requirement_index}")

                requirement_success = False
                self.error_handler.reset_tracking()
                self.reset_parameters()

                for attempt in range(max_attempts):
                    self.get_next_parameters()

                    try:
                        print(f"\nRequirement {requirement_index + 1}/{len(code_requirements)}, "
                              f"Attempt {attempt + 1}/{max_attempts}")

                        messages = self.build_chat_prompt(func, attempt)

                        # Add enhanced error context for the LLM if we have previous attempts
                        if attempt > 0 and self.history:
                            last_attempt = self.history[-1]
                            error_analysis_context = (
                                "\nPrevious Attempt (with analysis):\n"
                                f"{last_attempt.error}\n"
                            # this contains the code with all inline comments including stdout
                            )
                            print("error_analysis_context")
                            print(error_analysis_context)

                            # Add information about recurring errors
                            if hasattr(self.error_handler, 'error_count'):
                                recurring_patterns = [
                                    f"- {error}: appeared {count} times - needs fundamental redesign"
                                    for error, count in self.error_handler.error_count.items()
                                    if count > 1
                                ]
                                if recurring_patterns:
                                    error_analysis_context += (
                                            "\nPersistent Error Patterns to Resolve:\n" +
                                            "\n".join(recurring_patterns)
                                    )

                            messages.append({
                                'role': 'system',
                                'content': error_analysis_context
                            })

                        response = ollama.chat(
                            model="qwen2.5-coder",
                            messages=messages,
                            options=self.parameters
                        )

                        if not response or not isinstance(response, dict):
                            raise RuntimeError(f"Invalid response format from code generation: {response}")
                        print("llm response")
                        print(response['message']['content'])
                        code = self.extract_code(response)
                        print("extracted code from response")
                        print(code)
                        if not code or not code.strip():
                            raise ValueError("Generated code is empty")

                        code = self.clean_main_block(code)
                        print("cleaned code:")
                        print(code)
                        # Perform static analysis
                        analysis_results = self.error_handler.analyze_code(code)
                        if analysis_results and isinstance(analysis_results, dict):
                            if analysis_results.get('pylint_errors') or analysis_results.get('bandit_issues'):
                                error = RuntimeError("Static analysis found issues")
                                enhanced_error = self.error_handler.enhance_error(
                                    error,
                                    code,
                                    None
                                )
                                raise RuntimeError(enhanced_error)

                        # Install and test requirements
                        requirements = self.extract_requirements(code)
                        ret_code, stdout, stderr = self.install_requirements(requirements)
                        if ret_code != 0:
                            error = RuntimeError(f"Requirements installation failed: {stderr}")
                            enhanced_error = self.error_handler.enhance_error(
                                error,
                                code,
                                stdout if 'stdout' in locals() else None
                            )
                            raise RuntimeError(enhanced_error)

                        ret_code, stdout, stderr = self.execute_code(code)
                        if ret_code != 0:
                            error = RuntimeError(f"Code execution failed: {stderr}")
                            enhanced_error = self.error_handler.enhance_error(
                                error,
                                code,
                                stdout if 'stdout' in locals() else None
                            )
                            raise RuntimeError(enhanced_error)

                        self.add_attempt(code, "Success - no errors", stdout)
                        combined_code += code + "\n\n"
                        requirement_success = True
                        break

                    except Exception as e:
                        code_to_analyze = code if 'code' in locals() else func
                        enhanced_error = self.error_handler.enhance_error(e, code_to_analyze)
                        print(f"Attempt {attempt + 1} failed:\n{enhanced_error}")

                        self.add_attempt(
                            code_to_analyze,
                            enhanced_error,
                            stdout if 'stdout' in locals() else None
                        )

                        if attempt == max_attempts - 1:
                            if 'code' in locals():
                                combined_code += code + "\n\n"
                                requirement_success = True
                                break

                if not requirement_success:
                    return None

            # Combine and verify final code
            final_response = self._combine_code(combined_code)
            if not final_response:
                raise ValueError("Failed to combine code parts")

            final_code = self.extract_code(final_response)
            if not final_code or not final_code.strip():
                raise ValueError("Final code generation produced empty result")

            return final_code

        except Exception as e:
            print(f"Fatal error in process_with_reflection: {str(e)}")
            return None
