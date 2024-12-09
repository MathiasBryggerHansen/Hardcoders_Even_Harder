from pylint.lint import PyLinter
from pylint.reporters import JSONReporter
from bandit.core import manager
from bandit import config as b_config  # Changed this line
import yaml
import tempfile
import os
from io import StringIO
import sys
from typing import Dict, List
from error_handler import WebAppErrorHandler
# import inspect
import traceback


class EnhancedErrorHandler(WebAppErrorHandler):
    def __init__(self):
        super().__init__()
        self.static_analysis_results = None
        self.last_error = None
        self.error_count = 0
        self.error_history = []
        self.error_count = {}
        # Expand Pylint checks to include more error categories
        self.pylint_checks = [
            # Exception handling
            'bad-except-order',
            'raising-bad-type',
            'bad-exception-context',
            'bare-except',
            'broad-except',
            'duplicate-except',
            # General error prone conditions
            'undefined-variable',
            'undefined-loop-variable',
            'lost-exception',
            'return-in-finally',
            'unreachable',
            'dangerous-default-value',
            # Logic errors
            'not-callable',
            'assignment-from-none',
            'too-many-nested-blocks',
            'trailing-whitespace',
            'missing-final-newline'
        ]

        # Expand Bandit tests to include more security checks
        self.bandit_config = yaml.safe_dump({
            'tests': [
                'B101',  # Use of assert
                'B102',  # exec used
                'B103',  # Set bad file permissions
                'B104',  # Hardcoded bind all
                'B105',  # Hardcoded password string
                'B108',  # Hardcoded temp file
                'B110',  # try_except_pass
                'B112',  # Try_except_continue
                'B201',  # Flask debug mode
                'B301',  # Pickle usage
                'B324',  # Hashlib insecure hash functions
                'B506',  # Use of yaml load
                'B602',  # subprocess_popen_with_shell_equals_true
            ],
            'skips': [],
            'exclude_dirs': []
        })

    def _normalize_error(self, error_type: str, error_msg: str) -> str:
        """Normalize error messages to identify similar errors despite minor differences."""
        # Remove line numbers and specific variable names
        normalized = error_msg.lower()
        normalized = ' '.join(word for word in normalized.split()
                              if not word.isdigit() and not word.startswith(('line', 'at line')))
        return f"{error_type}:{normalized}"

    def analyze_code(self, code: str) -> Dict:
        """Analyze code using pylint and bandit for error handling patterns"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name

        try:
            all_pylint_results = self._run_pylint(temp_file_path)
            # Filter to only include errors and warnings
            pylint_results = [
                result for result in all_pylint_results
                if result['type'] in ('error', 'warning')
            ]
            bandit_results = self._run_bandit(temp_file_path)

            self.static_analysis_results = {
                'pylint_errors': pylint_results,  # Now only contains errors and warnings
                'bandit_issues': bandit_results,
                'error_patterns': self._identify_error_patterns(pylint_results, bandit_results)
            }

            return self.static_analysis_results
        finally:
            os.unlink(temp_file_path)

    def _run_pylint(self, file_path: str) -> List[Dict]:
        """Execute pylint analysis with properly formatted checker names"""
        reporter = JSONReporter()
        linter = PyLinter(reporter=reporter)

        # Initialize and load plugins
        linter.load_default_plugins()

        # Disable all checks first
        linter.disable('all')

        # Enable only specified checks by name
        for check in self.pylint_checks:
            linter.enable(check)

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            linter.check([file_path])
            return [
                {
                    'type': msg.category,
                    'module': msg.module,
                    'line': msg.line,
                    'message': msg.msg,
                    'message-id': msg.msg_id,
                    'symbol': msg.symbol
                }
                for msg in reporter.messages
            ]
        finally:
            sys.stdout = old_stdout

    def _run_bandit(self, file_path: str) -> List[Dict]:
        # Create a temporary config file with severity levels
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as config_file:
            yaml.safe_dump({
                'tests': ['B110', 'B112'],
                'skips': [],
                'exclude_dirs': [],
                # Add severity levels
                'test_config': {
                    'B110': {'level': 'MEDIUM'},
                    'B112': {'level': 'MEDIUM'}
                }
            }, config_file)
            config_path = config_file.name

        try:
            b_mgr = manager.BanditManager(
                b_config.BanditConfig(config_path),
                agg_type='file'
            )

            b_mgr.discover_files([file_path])
            b_mgr.run_tests()
            return b_mgr.get_issue_list()
        finally:
            os.unlink(config_path)

    def _identify_error_patterns(self, pylint_results: List[Dict],
                                 bandit_results: List['Issue']) -> List[str]:
        """Process and combine analysis results into meaningful patterns.

        Args:
            pylint_results: List of dictionaries containing Pylint results
            bandit_results: List of Bandit Issue objects

        Returns:
            List of formatted error pattern strings
        """
        patterns = []

        # Handle Pylint results (which are dictionaries)
        for result in pylint_results:
            if result['type'] in ('error', 'warning'):
                patterns.append(f"Line {result['line']}: {result['message']}")

        # Handle Bandit results (which are Issue objects)
        for issue in bandit_results:
            # Access Issue object attributes directly
            line_number = getattr(issue, 'line_number', None)
            if line_number is None:
                line_number = getattr(issue, 'lineno', 'unknown')

            issue_text = getattr(issue, 'issue_text', 'No description available')
            test_id = getattr(issue, 'test_id', 'unknown')

            patterns.append(
                f"Line {line_number}: {issue_text} (Test ID: {test_id})"
            )

        return patterns

    def reset_tracking(self):
        """Reset error tracking for a new function implementation."""
        self.error_history = []
        self.error_count = {}

    def enhance_error(self, error: Exception, source_code: str, stdout: str = None) -> str:
        """Enhance error messages by adding inline comments for errors and stdout prints.

        Args:
            error: The exception that occurred
            source_code: The source code being analyzed
            stdout: Optional stdout from code execution

        Returns:
            str: Source code with inline error comments and stdout annotations
        """
        error_type = type(error).__name__
        error_msg = str(error)

        # Track error pattern
        error_key = self._normalize_error(error_type, error_msg)
        self.error_count[error_key] = self.error_count.get(error_key, 0) + 1

        # Split code into lines while preserving empty lines
        code_lines = source_code.splitlines()
        annotated_lines = code_lines.copy()

        # Process stdout if available
        stdout_map = {}
        if stdout:
            current_line = None
            for line in stdout.splitlines():
                # Look for print statements in the code to map stdout
                for i, code_line in enumerate(code_lines):
                    if 'print(' in code_line and any(
                            token in line for token in code_line[code_line.index('print('):].split(')')[0]
                    ):
                        current_line = i
                        stdout_map[i] = stdout_map.get(i, []) + [line]

        # Add static analysis comments
        if self.static_analysis_results:
            # Process Pylint errors
            if 'pylint_errors' in self.static_analysis_results:
                for error in self.static_analysis_results['pylint_errors']:
                    if error['type'] in ('error', 'warning'):
                        line_num = error['line'] - 1  # Convert to 0-based index
                        if 0 <= line_num < len(annotated_lines):
                            comment = f"# {error['type'].upper()}: {error['message']} ({error['symbol']})"
                            annotated_lines[line_num] = f"{annotated_lines[line_num]:<80} {comment}"

            # Process Bandit issues
            if 'bandit_issues' in self.static_analysis_results:
                for issue in self.static_analysis_results['bandit_issues']:
                    line_num = issue.line_number - 1  # Convert to 0-based index
                    if 0 <= line_num < len(annotated_lines):
                        comment = f"# SECURITY: {issue.issue_text} (Test ID: {issue.test_id})"
                        annotated_lines[line_num] = f"{annotated_lines[line_num]:<80} {comment}"

        # Add stdout comments
        for line_num, outputs in stdout_map.items():
            if 0 <= line_num < len(annotated_lines):
                for output in outputs:
                    comment = f"# OUTPUT: {output}"
                    annotated_lines[line_num] = f"{annotated_lines[line_num]:<80} {comment}"

        # Add runtime error information
        tb = sys.exc_info()[2]
        if tb:
            for filename, line_num, func_name, text in traceback.extract_tb(tb):
                line_num -= 1  # Convert to 0-based index
                if 0 <= line_num < len(annotated_lines):
                    comment = f"# RUNTIME ERROR: {error_type}: {error_msg}"
                    annotated_lines[line_num] = f"{annotated_lines[line_num]:<80} {comment}"

        # Add warning about recurring errors if applicable
        if self.error_count[error_key] > 1:
            header_comment = [
                "# " + "=" * 78,
                f"# WARNING: This type of error has occurred {self.error_count[error_key]} times",
                f"# Consider a fundamentally different approach to fix: {error_msg}",
                "# " + "=" * 78,
                ""
            ]
            annotated_lines = header_comment + annotated_lines

        return '\n'.join(annotated_lines)

    def _find_repeated_patterns(self) -> str:
        """Analyze recent errors to identify recurring patterns."""
        if len(self.previous_errors) < 2:
            return ""

        # Count similar errors across recent attempts
        error_counts = {}
        for attempt_errors in self.previous_errors:
            for error in attempt_errors:
                key = f"{error['type']}:{error['message']}"
                error_counts[key] = error_counts.get(key, 0) + 1

        # Report errors that appear in multiple attempts
        repeated = [f"- {msg.split(':', 1)[1]} (occurred {count} times)"
                    for msg, count in error_counts.items()
                    if count >= 2]

        return "\n".join(repeated) if repeated else ""

    def reset_error_tracking(self):
        """Reset error tracking for a new function implementation."""
        self.previous_errors = []
        self.current_attempt = 0

    def _format_error_patterns(self) -> List[str]:
        """Format static analysis results into readable output"""
        if not self.static_analysis_results:
            return []

        formatted = []
        if self.static_analysis_results['error_patterns']:
            formatted.append("Identified Error Handling Patterns:")
            formatted.extend(f"- {pattern}"
                             for pattern in self.static_analysis_results['error_patterns'])

        return formatted

    def _format_error_history(self) -> List[str]:
        """Format error history analysis"""
        formatted = []
        error_counts = {}

        for error_type, _ in self.error_history:
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        if error_counts:
            formatted.append("Error Pattern Distribution:")
            for error_type, count in error_counts.items():
                formatted.append(f"- {error_type}: {count} occurrences")

        return formatted