from pylint.lint import PyLinter
from pylint.lint import PyLinter
from pylint.reporters import JSONReporter
from bandit.core import manager
from bandit import config as b_config
import yaml
import tempfile
import os
from io import StringIO
import sys
from typing import Dict, List, Union
from error_handler import WebAppErrorHandler
import traceback
from bandit.core.issue import Issue
from execution_module import Executor  # Updated import name


class EnhancedErrorHandler(WebAppErrorHandler):
    def __init__(self):
        super().__init__()
        self.static_analysis_results = None
        self.last_error = None
        self.error_history = []
        self.error_count = {}
        self.venv_path = None
        self.project_dir = os.getcwd()
        self.executor = Executor(project_dir=self.project_dir,error_handler=self)

        # Initialize virtual environment
        #self.executor.create_sandbox_environment()

        self.pylint_checks = [
            'bad-except-order',
            'raising-bad-type',
            'bad-exception-context',
            'bare-except',
            'broad-except',
            'duplicate-except',
            'undefined-variable',
            'undefined-loop-variable',
            'lost-exception',
            'return-in-finally',
            'unreachable',
            'dangerous-default-value',
            'not-callable',
            'assignment-from-none',
            'too-many-nested-blocks',
            'trailing-whitespace',
            'missing-final-newline'
        ]

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
            ret_code, stdout, stderr = self.executor.process_and_execute(code)
            all_pylint_results = self._run_pylint(temp_file_path)
            pylint_results = [
                result for result in all_pylint_results
                if result['type'] in ('error', 'warning')
            ]
            bandit_results = self._run_bandit(temp_file_path)



            self.static_analysis_results = {
                'pylint_errors': pylint_results,
                'bandit_issues': bandit_results,
                'error_patterns': self._identify_error_patterns(pylint_results, bandit_results),
                'stdout': stdout,
                'stderr': stderr,
                'return_code': ret_code
            }

            return self.static_analysis_results

        finally:
            os.unlink(temp_file_path)
            self.executor.cleanup()

    def _run_pylint(self, file_path: str) -> List[Dict]:
        """Execute pylint analysis with properly formatted checker names."""
        reporter = JSONReporter()
        linter = PyLinter(reporter=reporter)
        linter.load_default_plugins()
        linter.disable('all')

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
        """Execute bandit security analysis."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as config_file:
            yaml.safe_dump({
                'tests': ['B110', 'B112'],
                'skips': [],
                'exclude_dirs': [],
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
            results = b_mgr.get_issue_list()

            # Convert Issue objects to dictionaries if they aren't already
            return [
                issue if isinstance(issue, dict) else {
                    'line_number': getattr(issue, 'line_number', getattr(issue, 'lineno', None)),
                    'issue_text': getattr(issue, 'issue_text', 'No description available'),
                    'test_id': getattr(issue, 'test_id', 'unknown')
                }
                for issue in results
            ]
        finally:
            os.unlink(config_path)

    def _identify_error_patterns(self, pylint_results: List[Dict],
                               bandit_results: List[Union[Dict, Issue]]) -> List[str]:
        """Process and combine analysis results into meaningful patterns."""
        patterns = []

        for result in pylint_results:
            if result['type'] in ('error', 'warning'):
                patterns.append(f"Line {result['line']}: {result['message']}")

        for issue in bandit_results:
            # Handle both Issue objects and dictionaries
            if isinstance(issue, dict):
                line_number = issue.get('line_number') or issue.get('lineno', 'unknown')
                issue_text = issue.get('issue_text', 'No description available')
                test_id = issue.get('test_id', 'unknown')
            else:
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

    def enhance_error(self, error: Exception, code: str, stdout: str = None) -> str:
        """Enhance error messages by adding inline comments for errors and stdout prints."""
        error_type = type(error).__name__
        error_msg = str(error)

        error_key = self._normalize_error(error_type, error_msg)
        self.error_count[error_key] = self.error_count.get(error_key, 0) + 1

        captured_stdout = stdout if stdout else ""

        code_lines = code.splitlines()
        annotated_lines = code_lines.copy()
        stdout_map = {}

        if captured_stdout and captured_stdout.strip():
            stdout_lines = [line.strip() for line in captured_stdout.splitlines() if line.strip()]
            print_locations = [(i, line.strip()) for i, line in enumerate(code_lines)
                               if 'print(' in line.lstrip()]
            # Map each print statement to its corresponding output
            for idx, (line_num, _) in enumerate(print_locations):
                if idx < len(stdout_lines):
                    stdout_map[line_num] = [stdout_lines[idx]]
        if self.static_analysis_results:
            if 'pylint_errors' in self.static_analysis_results:
                for error in self.static_analysis_results['pylint_errors']:
                    if error['type'] in ('error', 'warning'):
                        line_num = error['line'] - 1
                        if 0 <= line_num < len(annotated_lines):
                            comment = f"# {error['type'].upper()}: {error['message']} ({error['symbol']})"
                            annotated_lines[line_num] = f"{annotated_lines[line_num]:<80} {comment}"

            if 'bandit_issues' in self.static_analysis_results:
                for issue in self.static_analysis_results['bandit_issues']:
                    try:
                        line_num = issue.line_number - 1 if hasattr(issue, 'line_number') else \
                            issue.lineno - 1 if hasattr(issue, 'lineno') else 0
                        if 0 <= line_num < len(annotated_lines):
                            comment = f"# SECURITY: {issue.issue_text} (Test ID: {issue.test_id})"
                            annotated_lines[line_num] = f"{annotated_lines[line_num]:<80} {comment}"
                    except AttributeError:
                        continue
        for line_num, outputs in stdout_map.items():
            if 0 <= line_num < len(annotated_lines):
                for output in outputs:
                    comment = f"# OUTPUT: {output}"
                    annotated_lines[line_num] = f"{annotated_lines[line_num]:<80} {comment}"

        tb = sys.exc_info()[2]
        if tb:
            for filename, line_num, func_name, text in traceback.extract_tb(tb):
                line_num -= 1
                if 0 <= line_num < len(annotated_lines):
                    comment = f"# RUNTIME ERROR: {error_type}: {error_msg}"
                    annotated_lines[line_num] = f"{annotated_lines[line_num]:<80} {comment}"

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

    def _format_error_patterns(self) -> List[str]:
        """Format static analysis results into readable output."""
        if not self.static_analysis_results:
            return []

        formatted = []
        if self.static_analysis_results['error_patterns']:
            formatted.append("Identified Error Handling Patterns:")
            formatted.extend(f"- {pattern}"
                             for pattern in self.static_analysis_results['error_patterns'])

        return formatted

    def _format_error_history(self) -> List[str]:
        """Format error history analysis."""
        formatted = []
        error_counts = {}

        for error_type, _ in self.error_history:
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        if error_counts:
            formatted.append("Error Pattern Distribution:")
            for error_type, count in error_counts.items():
                formatted.append(f"- {error_type}: {count} occurrences")

        return formatted