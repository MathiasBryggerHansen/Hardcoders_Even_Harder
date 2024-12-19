import sys
from io import StringIO
import traceback


class CodeAnnotator:
    def __init__(self):
        self.output = []
        self.captured_stdout = StringIO()

    def format_value(self, value):
        if isinstance(value, str):
            return f'"{value}"'
        return str(value)

    def trace_execution(self, frame, event, arg):
        if event == 'line':
            # Get the current line number and source code
            line_no = frame.f_lineno
            code_line = self.source_lines[line_no - 1].rstrip()

            # Get local variables for this line
            local_vars = frame.f_locals.copy()

            # Format variables that changed on this line
            var_changes = []
            for var, value in local_vars.items():
                if var not in self.prev_locals or self.prev_locals[var] != value:
                    var_changes.append(f"{var}={self.format_value(value)}")

            # Capture any stdout from this line
            stdout_content = self.captured_stdout.getvalue()
            self.captured_stdout.truncate(0)
            self.captured_stdout.seek(0)

            # Build the annotated line
            annotation = []
            if var_changes:
                annotation.append(", ".join(var_changes))
            if stdout_content:
                annotation.append(f"stdout={stdout_content.rstrip()}")

            annotated_line = code_line
            if annotation:
                annotated_line += f"  # → {', '.join(annotation)}"

            self.output.append(annotated_line)
            self.prev_locals = local_vars.copy()

        return self.trace_execution

    def annotate(self, func, *args, **kwargs):
        # Get the source code
        import inspect
        self.source_lines = inspect.getsource(func).splitlines()
        self.prev_locals = {}

        # Set up stdout capture
        old_stdout = sys.stdout
        sys.stdout = self.captured_stdout

        # Set up the tracer
        sys.settrace(self.trace_execution)

        try:
            # Execute the function
            func(*args, **kwargs)
        except Exception as e:
            # Add the error annotation
            last_line = self.source_lines[len(self.output)].rstrip()
            self.output.append(f"{last_line}  # {type(e).__name__}: {str(e)}")
        finally:
            # Clean up
            sys.settrace(None)
            sys.stdout = old_stdout

        return "\n".join(self.output)


# Example usage
def example_usage():
    def buggy_calc(x):
        a = x + 1
        print(a)
        y = len("a")
        b = x / 0
        return b * 2

    annotator = CodeAnnotator()
    annotated_code = annotator.annotate(buggy_calc, 1)
    print(annotated_code)


if __name__ == "__main__":
    example_usage()