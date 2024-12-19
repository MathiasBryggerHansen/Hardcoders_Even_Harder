import sys
import inspect
from typing import Dict, Any
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TraceEntry:
    line_no: int
    event: str
    changes: Dict[str, list]
    indent: int  # Added to track line indentation
    return_value: Any = None


class ValueTracer:
    def __init__(self):
        self.traces = []
        self.func_first_line = None
        self.error = None
        self.value_sequences = defaultdict(list)
        self.line_operations = set()

    def trace_function(self, frame, event, arg):
        """

        :param frame:
        :param event:
        :param arg:
        :return:
        """
        line_no = frame.f_lineno

        if self.func_first_line is None:
            self.func_first_line = frame.f_code.co_firstlineno

        if event in ('line', 'return'):
            current_locals = {
                k: v for k, v in frame.f_locals.items()
                if not k.startswith('__')
            }

            # Get source line and its indentation
            source_lines = inspect.getsourcelines(frame.f_code)[0]
            current_line = source_lines[line_no - frame.f_code.co_firstlineno]
            indent = len(current_line) - len(current_line.lstrip())

            # For each variable, check if this line modifies it
            for name, value in current_locals.items():
                if name in current_line.strip() and ('=' in current_line or '+=' in current_line):
                    self.line_operations.add((line_no, name))
                    last_values = self.value_sequences[(line_no, name)]
                    if not last_values or last_values[-1] != value:
                        self.value_sequences[(line_no, name)].append(value)

            # Create trace entry
            changes = {}
            for (trace_line, name), values in self.value_sequences.items():
                if trace_line == line_no and len(values) > 0:
                    changes[name] = values

            if changes or event == 'return':
                trace = TraceEntry(
                    line_no=line_no,
                    event=event,
                    changes=changes,
                    indent=indent,
                    return_value=arg if event == 'return' else None
                )
                if changes or event == 'return':
                    self.traces.append(trace)

        return self.trace_function


def format_value(v):
    """Format a value for display"""
    if isinstance(v, (int, float, bool)):
        return str(v)
    return repr(v)


def format_sequence(values):
    """Format a sequence of values with arrows"""
    return ' -> '.join(format_value(v) for v in values)


def show_traced_execution(func, *args, **kwargs):
    tracer = ValueTracer()


    source = inspect.getsource(func) #Returns function definition
    source_lines = source.splitlines() #Retrieve source codes as list of lines
    max_line_length = max(len(line.rstrip()) for line in source_lines)
    comment_position = max_line_length + 4  # Reduced padding before comments

    print(f"\nFunction: {func.__name__}")
    print("-" * 80)

    result = None
    error = None
    sys.settrace(tracer.trace_function) #Sets a tracer which records any stacktracevenets when trace_function is executed
    try:
        result = func(*args, **kwargs) #Runs func with provided arguments
    except Exception as e:
        error = e
        tracer.error = e
    finally:
        sys.settrace(None) #finally set tracer

    # Group traces by line number
    traces_by_line = defaultdict(list)
    for trace in tracer.traces: #traces logged in the tr
        relative_line = trace.line_no - tracer.func_first_line
        if 0 <= relative_line < len(source_lines):
            traces_by_line[relative_line].append(trace)

    for i, line in enumerate(source_lines):
        line_stripped = line.rstrip()
        print(line_stripped, end='')

        if i in traces_by_line:
            trace = traces_by_line[i][-1]
            if trace.changes or trace.return_value is not None:
                base_indent = trace.indent
                spaces_needed = comment_position - len(line_stripped.rstrip())
                if spaces_needed < 4:
                    spaces_needed = 4
                padding = " " * spaces_needed

                changes = []
                for name, values in trace.changes.items():
                    if len(values) > 0 and (trace.line_no, name) in tracer.line_operations:
                        changes.append(f"{name}={format_sequence(values)}")

                if trace.return_value is not None:
                    changes.append(f"returns {format_value(trace.return_value)}")

                if changes:
                    print(f"{padding}# → {', '.join(changes)}", end='')

                # Add error display here, at the line where it occurred
                if error and trace.line_no == tracer.traces[-1].line_no:
                    if not changes:  # If we haven't printed a comment yet
                        print(f"{padding}# → {type(error).__name__}: {str(error)}", end='')
                    else:  # Add to existing comment
                        print(f", {type(error).__name__}: {str(error)}", end='')
        print()

    # Remove or comment out the error message at the bottom
    print("-" * 80)
    if error:
        # print(f"Execution failed: {type(error).__name__}: {str(error)}")  # Remove or comment this
        print("Execution failed")  # Just indicate failure without details
    else:
        print(f"Final return value: {format_value(result)}")


# Test function
def analyze_data(data_dict):
    total = 0
    count = 0
    for key, value in data_dict.items():
        if isinstance(value, (int, float)):
            total += value
            count += 1
    return total / count if count > 0 else 0


if __name__ == "__main__":
    print("\nTesting normal case:")
    sample_data = {'a': 10, 'b': 20, 'c': 'string', 'd': 30}
    show_traced_execution(analyze_data, sample_data)

    print("\nTesting error case:")


    def buggy_calc(x):
        a = x + 1
        b = x / 0  # Will raise ZeroDivisionError
        return b * 2


    show_traced_execution(buggy_calc, 5)