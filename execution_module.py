import os
import tempfile
import subprocess
import venv
from typing import Tuple, List, Union, Set
import itertools
# import logging
import shutil
import traceback
import sys
import time
import virtualenv

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)


class Executor:
    def __init__(self, project_dir=None, error_handler=None):
        self.error_handler = error_handler
        self.venv_path = None
        self.project_dir = project_dir
        self.installed_packages: Set[str] = set()
        self._initialize_environment()

    def _initialize_environment(self):
        """Initialize or reinitialize the execution environment."""
        # logger.debug("Initializing execution environment")
        self.cleanup()  # Clean up any existing environment
        self.create_sandbox_environment(self.project_dir)

    def create_sandbox_environment(self, project_dir):
        """Create an isolated virtual environment for code execution using virtualenv."""
        try:
            self.project_dir = project_dir
            self.venv_path = os.path.join(self.project_dir, 'venv')

            # Clear previously installed packages
            self.installed_packages.clear()

            # Clean up any existing environment
            if os.path.exists(self.venv_path):
                shutil.rmtree(self.venv_path, ignore_errors=True)



            print(f"Creating virtual environment at: {self.venv_path}")
            virtualenv.cli_run([self.venv_path])

            # Get the pip path based on OS
            pip_path = os.path.join(self.venv_path, 'Scripts', 'pip.exe') if os.name == 'nt' \
                else os.path.join(self.venv_path, 'bin', 'pip')

            # Verify pip installation
            try:
                result = subprocess.run(
                    [pip_path, '--version'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(f"Pip version: {result.stdout.strip()}")
            except subprocess.CalledProcessError as e:
                print(f"Pip verification failed: {str(e)}")
                raise

            return True

        except Exception as e:
            print(f"Failed to create sandbox environment: {str(e)}")
            self.cleanup()
            raise

    def execute_code(self, code: str) -> Tuple[int, str, str]:
        """Execute code in the isolated environment.

        Args:
            code: The Python code to execute

        Returns:
            Tuple containing:
            - Return code (0 for success, 1 for failure)
            - stdout output
            - stderr output or error message
        """
        temp_file_path = None
        print("EXECUTING CODE!!")
        try:
            # Ensure environment is ready
            if not self.venv_path or not os.path.exists(self.venv_path):
                self._initialize_environment()

            # Compile check
            try:
                compile(code, '<string>', 'exec')
            except Exception as e:
                error = self.error_handler.enhance_error(e, code) if self.error_handler else str(e)
                return 1, "", error

            # Create temporary file
            temp_file_path = os.path.join(self.project_dir, f'temp_{os.urandom(4).hex()}.py')
            with open(temp_file_path, 'w') as temp_file:
                temp_file.write(code)

            # Get Python interpreter path
            python_path = os.path.join(self.venv_path, 'Scripts', 'python.exe') if os.name == 'nt' \
                else os.path.join(self.venv_path, 'bin', 'python')

            if not os.path.exists(python_path):
                raise RuntimeError(f"Python interpreter not found at {python_path}")
            # Execute code
            try:
                result = subprocess.run(
                    [python_path, temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=2
                )

                return result.returncode, result.stdout, result.stderr

            except subprocess.TimeoutExpired:
                error = "Code execution timed out - check for infinite loops"
                return 1, "", error

        except Exception as e:
            return 1, "", str(e)

        finally:
            # Cleanup temporary file but preserve the environment
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    print(f"Warning: Failed to clean up temporary file: {e}")


    def cleanup(self):
        """Clean up the environment."""
        # logger.debug("Cleaning up environment")
        if self.project_dir and os.path.exists(self.project_dir):
            try:
                shutil.rmtree(self.project_dir)
                # logger.debug(f"Removed project directory: {self.project_dir}")
                self.project_dir = None
                self.venv_path = None
                self.installed_packages.clear()
            except Exception as e:
                print(f"Error cleaning up environment: {e}")

    def process_and_execute(self, response: str) -> Tuple[int, str, str]:
        """Process and execute code with proper environment management."""
        try:
            # logger.info("Starting code processing and execution")

            # Extract and process code
            code = self.extract_code(response)
            # logger.debug(f"Extracted code:\n{code}")

            # Handle requirements
            requirements = self.extract_requirements(code)
            if requirements:
                # logger.debug(f"Installing requirements: {requirements}")
                ret_code, stdout, stderr = self.install_requirements(requirements)
                if ret_code != 0:
                    # logger.error(f"Failed to install requirements: {stderr}")
                    return ret_code, stdout, stderr

            # Execute code
            ret_code, stdout, stderr = self.execute_code(code)
            # logger.info(f"Execution completed with return code: {ret_code}")

            return ret_code, stdout, stderr

        except Exception as e:
            # logger.error(f"Error in process_and_execute: {str(e)}", exc_info=True)
            return 1, "", str(e)

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

            if result.returncode == 0:
                self.installed_packages.update(new_requirements)

            return result.returncode, result.stdout, result.stderr

        except Exception as e:
            print(f"Exception during pip install: {str(e)}")  # Debug exception
            return 1, "", str(e)

# import os
# import tempfile
# import subprocess
# import venv
# from typing import Tuple, List, Union, Set
# import itertools
#
#
# class Executor:
#     def __init__(self, error_handler=None):
#         self.error_handler = error_handler #EnhancedErrorHandler()
#         self.venv_path = None
#         self.project_dir = None
#         self.installed_packages: Set[str] = set()
#         self.create_sandbox_environment()
#
#     def create_sandbox_environment(self):
#         """Create an isolated virtual environment for code execution."""
#         self.project_dir = tempfile.mkdtemp()
#
#         self.venv_path = os.path.join(self.project_dir, 'venv')
#
#         # Clear any previously installed packages
#         self.installed_packages.clear()
#
#         try:
#             venv.create(self.venv_path, with_pip=True)
#
#             # Verify pip exists
#             pip_path = os.path.join(self.venv_path, 'Scripts', 'pip.exe') if os.name == 'nt' \
#                 else os.path.join(self.venv_path, 'bin', 'pip')
#
#             if not os.path.exists(pip_path):
#                 raise RuntimeError(f"Pip not found at {pip_path}")
#
#             # Test pip installation
#             test_result = subprocess.run(
#                 [pip_path, '--version'],
#                 capture_output=True,
#                 text=True
#             )
#             if test_result.returncode != 0:
#                 raise RuntimeError(f"Pip test failed: {test_result.stderr}")
#
#         except Exception as e:
#             self.cleanup()
#             raise
#
#
#

#

#
#
#     def cleanup(self):
#         """Clean up the environment."""
#         if self.project_dir and os.path.exists(self.project_dir):
#             try:
#                 import shutil
#                 shutil.rmtree(self.project_dir)
#                 self.project_dir = None
#                 self.venv_path = None
#                 self.installed_packages.clear()
#             except Exception as e:
#                 print(f"Error cleaning up environment: {e}")
#
#     def process_and_execute(self, response: str):
#         code = self.extract_code(response)
#         # code = self.clean_main_block(code)
#         requirements = self.extract_requirements(code)
#         ret_code, stdout, stderr = self.install_requirements(requirements)
#         ret_code, stdout, stderr = self.execute_code(code)

#         print(f"||||||||||stdout: {stdout}||||||||||")
#
#         return ret_code, stdout, stderr

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
                else:  # Keep ALL other non-empty lines
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

    def execute_code(self, code: str) -> Tuple[int, str, str]:
        """Execute code in the isolated environment."""
        temp_file_path = None
        try:
            # Try to compile the code first to catch syntax errors

            try:
                #CODE COMPILATION CONFIRMED TO RUN
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

            #Result indicated whether or not the executed code could compile
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
