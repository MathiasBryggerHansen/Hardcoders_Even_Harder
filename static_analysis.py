from pylint.lint import Run
from pylint.reporters import BaseReporter
from io import StringIO
import tempfile
import os
import sys
from typing import Dict, List, Union
import traceback
import subprocess
from pylint.reporters import JSONReporter
import json
import execution_module


class CaptureReporter(BaseReporter):
    def __init__(self):
        super().__init__()
        self.output = StringIO()


    def handle_message(self, msg):
        # Only capture errors and warnings, ignore other message types
        if msg.category in ('error', 'warning'):
            self.output.write(str(msg) + '\n')

    def _display(self, layout):
        pass


class EnhancedErrorHandler:
    def __init__(self):
        self.static_analysis_results = None
        self.last_error = None
        self.error_history = []
        self.error_count = {}
        self.project_dir = os.getcwd()
        self.executor = execution_module.Executor(project_dir = self.project_dir, error_handler=self)


        # Focus on the most critical Pylint checks that indicate actual problems
        self.important_checks = [
            # Error detection
            'undefined-variable',  # Using undefined variables
            'undefined-loop-variable',  # Using loop variables outside loop
            'not-callable',  # Trying to call non-callable objects
            'no-member',  # Accessing non-existent members
            'assignment-from-none',  # Using None in operations

            # Logic errors
            'unreachable',  # Unreachable code
            'return-in-finally',  # Return in finally block
            'inconsistent-return-statements',  # Inconsistent return types

            # Exception handling
            'bare-except',  # Too broad exception handling
            'raising-bad-type',  # Raising invalid exceptions
            'bad-except-order',  # Wrong order of except clauses
            'lost-exception',  # Exception context being lost

            # Security
            'exec-used',  # Use of exec()
            'eval-used',  # Use of eval()

            # Critical design issues
            'duplicate-code',  # Significant code duplication
            'too-many-nested-blocks'  # Overly complex code structure
        ]

    def analyze_code(self, code: str) -> dict:
        """Analyze code for critical issues using focused Pylint checks."""
        try:
            code = code.encode('utf-8', 'ignore').decode('utf-8')
            python_path = self.executor._get_python_path()

            # Find the starting line number of the code snippet
            lines = code.splitlines()

            # Find first non-empty line
            start_index = 0
            for i, line in enumerate(lines):
                if line.strip():
                    start_index = i
                    break

            # Rejoin remaining lines
            '\n'.join(lines[start_index:])

            # Create temp file for analysis
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8',
                                             dir=os.getcwd()) as temp_file:
                temp_file.write(code)
                temp_file.flush()

            temp_file_path = temp_file.name

            # Run Pylint analysis
            # Create a string buffer to capture the output
            output = StringIO()

            # Use JSONReporter instead of text reporter for better parsing
            reporter = JSONReporter(output)

            # Configure Pylint options
            options = [
                temp_file_path,
                '--disable=all',  # First disable all checks
                '--enable=E,W,F,R,C',  # Then enable the ones we want
                '--max-line-length=100',
                '--persistent=no',
                '--reports=no',
                '--score=no',
                '--msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}"'
            ]

            # Run Pylint with configured options
            Run(options, reporter=reporter, exit=False)

            # Get the JSON output
            try:
                pylint_output = json.loads(output.getvalue())
            except json.JSONDecodeError:
                return []  # Return empty list if no errors found

            # Process and format the results
            pylint_results = []
            for message in pylint_output:
                error_info = {
                    'type': message.get('type', 'unknown'),
                    'line': message.get('line', 0),
                    'column': message.get('column', 0),
                    'path': message.get('path', ''),
                    'symbol': message.get('symbol', ''),
                    'message': message.get('message', ''),
                    'message-id': message.get('message-id', '')
                }
                pylint_results.append(error_info)

            # Run Bandit analysis
            bandit_output = subprocess.run(
                [sys.executable, '-m', 'bandit', '-f', 'json', temp_file_path],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            bandit_results = json.loads(bandit_output.stdout) if bandit_output.stdout else {}

            # Process Bandit results to remove consecutive duplicates
            filtered_bandit_results = []
            previous_bandit_issue = None

            for issue in bandit_results.get('results', []):
                # Create a unique identifier for the bandit issue
                issue_key = f"{issue.get('issue_text')}_{issue.get('test_id')}"

                if issue_key != previous_bandit_issue:
                    filtered_bandit_results.append(issue)
                    previous_bandit_issue = issue_key

            self.static_analysis_results = {
                'pylint_errors': pylint_results,
                'bandit_issues': filtered_bandit_results,
                'error_patterns': self._extract_error_patterns(pylint_results, {'results': filtered_bandit_results})
            }

            return self.static_analysis_results
        except Exception as e:
            print(f"Error during static analysis {e}")
            return {'error': str(e)}

        finally:
            try:
                temp_file.close()
                os.unlink(temp_file_path)
            except Exception as e:
                print(f"Error during static analysis cleanup {e}")



    def _remove_duplicates(self, results: List[Dict]) -> List[Dict]:
        """Remove consecutive duplicate error messages."""
        if not results:
            return []

        filtered = []
        prev_msg = None

        for result in results:
            current_msg = result.get('msg', result.get('issue_text', ''))
            if current_msg != prev_msg:
                filtered.append(result)
                prev_msg = current_msg

        return filtered

    def _extract_error_patterns(self, pylint_results: List[Dict],
                                bandit_results: Dict[str, List]) -> List[str]:
        """Extract meaningful error patterns from analysis results."""
        patterns = []

        # Process critical Pylint errors
        for result in pylint_results:
            if result.get('type') in ('error', 'warning'):
                patterns.append(f"Line {result['line']}: {result['message']}")

        # Process security issues
        for issue in bandit_results['results']:
            line_number = issue.get('line_number', 'unknown')
            issue_text = issue.get('issue_text', 'No description available')
            test_id = issue.get('test_id', 'unknown')
            patterns.append(f"Line {line_number}: {issue_text} (Test ID: {test_id})")

        return patterns

    def enhance_error(self, error: Exception, code: str, stdout: str = None) -> str:
        """Enhance error messages with focused analysis results."""
        error_type = type(error).__name__
        error_msg = str(error)

        # Track error frequency
        error_key = f"{error_type}:{error_msg.lower()}"
        self.error_count[error_key] = self.error_count.get(error_key, 0) + 1

        code_lines = code.splitlines()
        annotated_lines = code_lines.copy()

        # Add static analysis annotations
        if self.static_analysis_results:
            for error in self.static_analysis_results['pylint_errors']:
                line_num = error['line'] - 1
                if 0 <= line_num < len(annotated_lines):
                    comment = f"# {error['type'].upper()}: {error['message']}"
                    annotated_lines[line_num] = f"{annotated_lines[line_num]:<80} {comment}"

        # Add runtime error annotations
        tb = sys.exc_info()[2]
        if tb:
            for _, line_num, _, _ in traceback.extract_tb(tb):
                line_num -= 1
                if 0 <= line_num < len(annotated_lines):
                    comment = f"# RUNTIME ERROR: {error_type}: {error_msg}"
                    annotated_lines[line_num] = f"{annotated_lines[line_num]:<80} {comment}"

        # Add header for recurring errors
        if self.error_count[error_key] > 1:
            header = [
                "# " + "=" * 78,
                f"# WARNING: This error has occurred {self.error_count[error_key]} times",
                f"# Consider a different approach to fix: {error_msg}",
                "# " + "=" * 78,
                ""
            ]
            annotated_lines = header + annotated_lines

        return '\n'.join(annotated_lines)

    def reset_tracking(self):
        """Reset error tracking for a new analysis session."""
        self.error_history = []
        self.error_count = {}
        self.static_analysis_results = None