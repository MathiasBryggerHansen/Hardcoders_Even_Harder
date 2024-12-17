def _setup_venv(self):
    """Set up a virtual environment for code execution."""
    self.project_dir = tempfile.mkdtemp()
    self.venv_path = os.path.join(self.project_dir, 'venv')

    try:
        venv.create(self.venv_path, with_pip=True)
    except Exception as e:
        self._cleanup_venv()
        raise RuntimeError(f"Failed to create virtual environment: {e}")


def _cleanup_venv(self):
    """Clean up the virtual environment."""
    if self.project_dir and os.path.exists(self.project_dir):
        try:
            import shutil
            shutil.rmtree(self.project_dir)
            self.project_dir = None
            self.venv_path = None
        except Exception as e:
            print(f"Error cleaning up environment: {e}")


def _execute_in_venv(self, code: str) -> tuple[int, str, str]:
    """Execute code in virtual environment and capture stdout."""
    if not self.venv_path:
        self._setup_venv()

    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name

        python_path = os.path.join(self.venv_path, 'Scripts', 'python.exe') if os.name == 'nt' \
            else os.path.join(self.venv_path, 'bin', 'python')

        result = subprocess.run(
            [python_path, temp_file],
            capture_output=True,
            text=True,
            timeout=2
        )

        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        return 1, "", "Code execution timed out"
    except Exception as e:
        return 1, "", str(e)
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception:
                pass
#%% Unmodified process_with_reflection() (Modified is currently used as of this commit)
# def process_with_reflection(self, code_requirements: list, max_attempts: int = 20, dummy_mode = False) -> Optional[str]:
    #     """Process code requirements with multiple attempts and enhanced error handling.
    #
    #     Args:
    #         code_requirements (list): List of code requirements to implement
    #         max_attempts (int): Maximum number of attempts per requirement
    #
    #     Returns:
    #         Optional[str]: The successfully combined and tested code, or None if attempts fail
    #     """
    #     if not code_requirements:
    #         raise ValueError("Code requirements list cannot be empty")
    #     combined_code = ""
    #
    #     try:
    #
    #         for requirement_index, func in enumerate(code_requirements):
    #             if not isinstance(func, str) or not func.strip():
    #                 raise ValueError(f"Invalid requirement at index {requirement_index}")
    #
    #             requirement_success = False
    #             self.error_handler.reset_tracking()
    #             self.reset_parameters()
    #
    #             for attempt in range(max_attempts):
    #                 self.get_next_parameters()
    #
    #                 try:
    #                     print(f"\nRequirement {requirement_index + 1}/{len(code_requirements)}, "
    #                           f"Attempt {attempt + 1}/{max_attempts}")
    #
    #                     messages = self.build_chat_prompt(func, attempt)
    #
    #                     # Add enhanced error context for the LLM if we have previous attempts
    #                     if attempt > 0 and self.history:
    #                         last_attempt = self.history[-1]
    #                         error_analysis_context = (
    #                             "\nPrevious Attempt (with analysis):\n"
    #                             f"{last_attempt.error}\n"
    #                         # this contains the code with all inline comments including stdout
    #                         )
    #                         # print("error_analysis_context")
    #                         # print(error_analysis_context)
    #
    #                         # Add information about recurring errors
    #                         if hasattr(self.error_handler, 'error_count'):
    #                             recurring_patterns = [
    #                                 f"- {error}: appeared {count} times - needs fundamental redesign"
    #                                 for error, count in self.error_handler.error_count.items()
    #                                 if count > 1
    #                             ]
    #                             if recurring_patterns:
    #                                 error_analysis_context += (
    #                                         "\nPersistent Error Patterns to Resolve:\n" +
    #                                         "\n".join(recurring_patterns)
    #                                 )
    #
    #                         messages.append({
    #                             'role': 'system',
    #                             'content': error_analysis_context
    #                         })
    #
    #
    #                     if not dummy_mode:
    #                         response = ollama.chat(
    #                             model="qwen2.5-coder",
    #                             messages=messages,
    #                             options=self.parameters
    #                         )
    #
    #
    #                         if 'response' not in locals():
    #                             raise RuntimeError(f"Invalid response format from code generation: {response}")
    #                         # print("llm response")
    #                         # print(response['message']['content'])
    #                         code = self.executor.extract_code(response)
    #                         print("extracted code from response")
    #                         print(code)
    #                         if not code or not code.strip():
    #                             raise ValueError("Generated code is empty")
    #
    #                         code = self.executor.clean_main_block(code)
    #
    #                     else:
    #                         code = code_requirements[requirement_index]
    #
    #                     print("analyzing1:")
    #                     # print(code)
    #                     # Perform static analysis
    #                     analysis_results = self.error_handler.analyze_code(code)
    #                     if 'analysis_results' in locals():
    #                         if analysis_results.get('pylint_errors') or analysis_results.get('bandit_issues'):
    #                             error = RuntimeError("Static analysis found issues")
    #                             enhanced_error = self.error_handler.enhance_error(
    #                                 error,
    #                                 code,
    #                                 None
    #                             )
    #                             raise RuntimeError(enhanced_error)
    #
    #
    #                     # Install and test requirements
    #                     requirements = self.executor.extract_requirements(code)
    #                     ret_code, stdout, stderr = self.executor.install_requirements(requirements)
    #                     if ret_code != 0:
    #                         error = RuntimeError(f"Requirements installation failed: {stderr}")
    #                         enhanced_error = self.error_handler.enhance_error(
    #                             error,
    #                             code,
    #                             stdout if 'stdout' in locals() else None
    #                         )
    #                         raise RuntimeError(enhanced_error)
    #                     print("code")
    #                     print(code)
    #                     ret_code, stdout, stderr = self.executor.execute_code(code)
    #                     print("print(ret_code, stdout, stderr)")
    #                     print(ret_code, stdout, stderr)
    #
    #
    #                     if ret_code != 0:
    #                         error = RuntimeError(f"Code execution failed: {stderr}")
    #                         enhanced_error = self.error_handler.enhance_error(
    #                             error,
    #                             code,
    #                             stdout if 'stdout' in locals() else None
    #                         )
    #                         raise RuntimeError(enhanced_error)
    #                     print("CODE EXECUTED SUCCESSFULLY")
    #                     self.add_attempt(code, "Success - no errors", stdout)
    #                     combined_code += code + "\n\n"
    #                     requirement_success = True
    #                     break
    #
    #                 except Exception as e:
    #                     code_to_analyze = code if 'code' in locals() else func
    #                     enhanced_error = self.error_handler.enhance_error(e, code_to_analyze)
    #                     print(f"Attempt {attempt + 1} failed:\n{enhanced_error}")
    #
    #                     self.add_attempt(
    #                         code_to_analyze,
    #                         enhanced_error,
    #                         stdout if 'stdout' in locals() else None
    #                     )
    #
    #                     if attempt == max_attempts - 1:
    #                         if 'code' in locals():
    #                             combined_code += code + "\n\n"
    #                             requirement_success = True
    #                             break
    #
    #             if not requirement_success:
    #                 return None
    #
    #         # Combine and verify final code
    #         final_response = self._combine_code(combined_code)
    #         if not final_response:
    #             raise ValueError("Failed to combine code parts")
    #
    #         final_code = self.extract_code(final_response)
    #         if not final_code or not final_code.strip():
    #             raise ValueError("Final code generation produced empty result")
    #
    #         return final_code
    #
    #     except Exception as e:
    #         print(f"Fatal error in process_with_reflection: {str(e)}")
    #         return None