import os
from datetime import datetime
from collections import deque
from dataclasses import dataclass
from typing import Optional
from static_analysis import EnhancedErrorHandler
import ollama
# from execution_module import Executor

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
        self.project_dir = os.getcwd()
        # self.installed_packages: Set[str] = set()
        self.error_handler = EnhancedErrorHandler()
        # self.executor = self.error_handler.executor
        # self.create_sandbox_environment()
        self.parameters = {'temperature': 1, 'top_p': 0.9, 'top_k': 50}

    # def filter_lines(self, text, ignore_keyword):
    #     """Filter out lines containing the ignore keyword."""
    #     lines = text.strip().splitlines()
    #     return [line for line in lines if ignore_keyword not in line]

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

                combined_code = self.executor.extract_code(response)
                if not combined_code or not combined_code.strip():
                    raise ValueError("Generated empty code")

                combined_code = self.executor.clean_main_block(combined_code)

                # Analyze and test the code
                analysis_results = self.error_handler.analyze_code(combined_code)
                if analysis_results and isinstance(analysis_results, dict):
                    if analysis_results.get('pylint_errors') or analysis_results.get('bandit_issues'):
                        raise RuntimeError("Static analysis found issues")

                requirements = self.executor.extract_requirements(combined_code)
                ret_code, stdout, stderr = self.executor.install_requirements(requirements)
                if ret_code != 0:
                    raise RuntimeError(f"Requirements installation failed: {stderr}")

                ret_code, stdout, stderr = self.executor.execute_code(combined_code) #TODO: convert to process_and_execute
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
            self.parameters['top_p'] = min(0.95, 0.9 + 0.01 * (max_error_count - 1))
            self.parameters['temperature'] = min(2, 1 + 0.2 * (max_error_count - 1))
            self.parameters['top_k'] = min(50 + max_error_count * 10, 100)

            # print(f"Current error counts: {error_counts}")
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

    def build_chat_prompt(self, code_requirements: str, attempt: int) -> list[dict[str, str]]:
        """Build the chat prompt based on attempt number and any recurring error patterns."""
        messages = [{
            'role': 'system',
            'content': "You are designed to generate python functions that adheres to all requirements. Warnings and "
                       "errors thrown by the previous code iteration are commented on the relevant lines. All debugging"
                       "prints should be exposed (to stdout) when the code is executed. The code output should ***NOT**"
                       "* be in the form of an app."
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
            user_message += "ADD prints for debugging purposes WITHIN the code and ADD test code - do not using app logging."

        user_message += "\nEnclose code in ```python ``` tags. \n"
        messages.append({
            'role': 'user',
            'content': user_message
        })

        # Add debug print to see the messages being sent to the LLM
        print("\nDEBUG: Messages being sent to LLM:")
        for msg in messages:
            print(f"\nRole: {msg['role']}")
            print("Content:")
            print(msg['content'])
            print("-" * 80)

        return messages

    def reset_parameters(self) -> None:
        """Reset model parameters to their default values."""
        self.parameters = {
            'temperature': 1,
            'top_p': 0.9,
            'top_k': 50
        }

    def process_with_reflection(self, code_requirements: list, max_attempts: int = 20, dummy_mode=False): #-> Optional[execute_code: str]:
        if not code_requirements:
            raise ValueError("Code requirements list cannot be empty")

        combined_code = ""

        try:
            for requirement_index, func in enumerate(code_requirements):
                if not isinstance(func, str) or not func.strip():
                    raise ValueError(f"Invalid requirement at index {requirement_index}")

                requirement_success = False
                self.error_handler.reset_tracking()
                self.reset_parameters()

                for attempt in range(max_attempts):
                    self.get_next_parameters()
                    code = ""
                    try:
                        print(f"\nRequirement {requirement_index + 1}/{len(code_requirements)}, "
                              f"Attempt {attempt + 1}/{max_attempts}")

                        messages = self.build_chat_prompt(func, attempt)

                        if not dummy_mode:
                            response = ollama.chat(
                                model="qwen2.5-coder",
                                messages=messages,
                                options=self.parameters
                            )

                            code = self.error_handler.executor.extract_code(response)

                            # packages = self.error_handler.executor.extract_packages(code)

                            if not code or not code.strip():
                                raise ValueError("Generated code is empty")

                            code = self.error_handler.executor.clean_main_block(code) #TODO: consider if app() call is better to remove
                        else:
                            code = code_requirements[requirement_index]

                        # Static analysis now uses the persistent environment
                        analysis_results = self.error_handler.analyze_code(code)
                        if analysis_results.get('pylint_errors') or analysis_results.get('bandit_issues'):
                            error = RuntimeError("Static analysis found issues")
                            enhanced_error = self.error_handler.enhance_error(error, code)
                            raise RuntimeError(enhanced_error) #TODO: Where is this going?

                        # Use process_and_execute for consistent environment handling
                        ret_code, stdout, stderr = self.error_handler.executor.process_and_execute(code)
                        print("ret_code, stdout, stderr:")
                        print(ret_code, stdout, stderr)
                        if ret_code != 0:
                            error = RuntimeError(f"Code execution failed: {stderr}")
                            enhanced_error = self.error_handler.enhance_error(error, code, stdout)
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
                    # finally:
                    #     if dummy_mode:
                    #         break

                if not requirement_success:
                    return None

            # Use process_and_execute for final combination
            final_code = self._combine_code(combined_code)
            if not final_code:
                raise ValueError("Failed to combine code parts")

            return final_code

        except Exception as e:
            print(f"Fatal error in process_with_reflection: {str(e)}")
            return None


if __name__ == "__main__":
    handler = CodeEvolutionHandler()
    code_requirements = [
        "validate_request_format(request_data) -> tuple[bool, str] - Verify JSON data has required fields (email, age, subscription_tier, user_data) with correct data types. Handle: malformed JSON -> 400, missing/null fields -> 400, invalid data types -> 422. Return (is_valid, error_msg)",

        "validate_user_data(user_data) -> tuple[bool, str] - Check user_data contains valid preferences (notifications bool, theme str), payment_info (method, currency), and usage_metrics (array[3-10] of numbers). Handle: array index out of bounds -> 500, type conversion errors -> 422. Return (is_valid, error_msg)",

        "validate_business_rules(email, age, subscription_tier) -> tuple[bool, str] - Validate email is @validcompany.com, age is 18-100, subscription_tier in ['basic', 'pro', 'enterprise']. Handle: type conversion errors -> 422. Return (is_valid, error_msg)",

        "calculate_metrics(age, usage_metrics, payment_method, subscription_tier) -> dict - Calculate price (basic:$10, pro:$25, enterprise:$50), risk_score (age * avg_usage / 10), premium_multiplier (1.5 if crypto). Handle: division by zero -> 500, integer overflow -> 500. Return calculated metrics dict",

        "process_request() -> Response - Main /api/process POST handler: check rate limit (429 if exceeded), validate data (400/422 for validation fails), calculate metrics (500 for calculation errors), add timestamp and renewal_date, return appropriate HTTP response",

        "get_rate_limit_status(ip_address) -> tuple[bool, int] - Track and check if IP exceeded 5 requests/minute, return (is_allowed, current_count). Handle concurrent access to rate limit data",

        "get_system_metrics() -> dict - Get current memory usage and system uptime statistics. Handle potential OS-level errors -> 500",

        "health_check() -> Response - Handle /api/health GET requests: return system metrics and rate limit counts. Handle service unavailability -> 503",

        "Error handlers: handle_bad_request() -> 400 for malformed JSON/missing/null fields, handle_validation_error() -> 422 for invalid data types/values, handle_rate_limit() -> 429 for rate exceeded, handle_server_error() -> 500 for calculation/overflow/division errors"
    ]

    code_requirements = [
"""

    
global z


if x > 10:
    if x > 20:
        if x > 30:
            if x > 40:
                print("Nested conditions!")

"""]
# """
# print("hello frigfjas")
#
# token = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=16))
# return token
#
# a=b
# """]



    results = handler.process_with_reflection(code_requirements, dummy_mode = True)
