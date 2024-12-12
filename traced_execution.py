import sys
import inspect
import traceback
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TraceEntry:
    line_no: int
    event: str
    locals: Dict[str, Any]
    return_value: Any = None


class ValueTracer:
    def __init__(self):
        self.traces = []
        self.line_hits = defaultdict(int)
        self.func_first_line = None
        self.error = None

    def trace_function(self, frame, event, arg):
        line_no = frame.f_lineno

        if self.func_first_line is None:
            self.func_first_line = frame.f_code.co_firstlineno

        if event == 'line':
            self.line_hits[line_no] += 1

        current_locals = {
            k: v for k, v in frame.f_locals.items()
            if not k.startswith('__')
        }

        trace = TraceEntry(
            line_no=line_no,
            event=event,
            locals=current_locals,
            return_value=arg if event == 'return' else None
        )
        self.traces.append(trace)

        return self.trace_function


def format_value(v):
    """Format a value for display"""
    if isinstance(v, (int, float, bool)):
        return str(v)
    return repr(v)


def show_traced_execution(func, *args, **kwargs):
    tracer = ValueTracer()

    source = inspect.getsource(func)
    source_lines = source.splitlines()

    max_line_length = max(len(line.rstrip()) for line in source_lines)
    comment_position = max_line_length + 8

    print(f"\nFunction: {func.__name__}")
    print("-" * 80)

    result = None
    error = None
    sys.settrace(tracer.trace_function)
    try:
        result = func(*args, **kwargs)
    except Exception as e:
        error = e
        tracer.error = e
    finally:
        sys.settrace(None)

    traces_by_line = defaultdict(list)
    for trace in tracer.traces:
        traces_by_line[trace.line_no].append(trace)

    last_values = {}
    for i, line in enumerate(source_lines):
        line_stripped = line.rstrip()
        actual_line_no = tracer.func_first_line + i + 1  # Added +1 here
        line_traces = traces_by_line.get(actual_line_no, [])

        if line_traces:
            trace = line_traces[0]
            changes = []

            for name, value in trace.locals.items():
                if name not in last_values or last_values[name] != value:
                    change = f"{name}={format_value(value)}"
                    if line_stripped.replace(' ', '') != change.replace(' ', ''):
                        changes.append(change)
                    last_values[name] = value

            if trace.return_value is not None:
                changes.append(f"returns {format_value(trace.return_value)}")

            if changes:
                padding = " " * (comment_position - len(line_stripped))
                print(f"{line_stripped}{padding}# → {', '.join(changes)}")
            else:
                print(line_stripped)

            # If this was where the error occurred, show it
            if error and actual_line_no == tracer.traces[-1].line_no:
                print(f"{' ' * comment_position}# !!! {type(error).__name__}: {str(error)}")

            hit_count = tracer.line_hits[actual_line_no]
            if hit_count > 1:
                for t in line_traces[1:]:
                    changes = []
                    for name, value in t.locals.items():
                        if last_values.get(name) != value:
                            change = f"{name}={format_value(value)}"
                            if line_stripped.replace(' ', '') != change.replace(' ', ''):
                                changes.append(change)
                            last_values[name] = value
                    if changes:
                        print(f"{' ' * comment_position}# → {', '.join(changes)}")
        else:
            print(line_stripped)

    print("-" * 80)
    if error:
        print(f"Execution failed: {type(error).__name__}: {str(error)}")
    else:
        print(f"Final return value: {format_value(result)}")


# Test functions
def calculate_sum(x, y):
    a = x + y
    b = a * 2
    return b


def process_numbers(numbers, threshold):
    result = 0
    for num in numbers:
        if num > threshold:
            result += num
    return result


def analyze_data(data_dict):
    total = 0
    count = 0
    for key, value in data_dict.items():
        if isinstance(value, (int, float)):
            total += value
            count += 1
    return total / count if count > 0 else 0


def failing_function(x):
    a = x + 1
    b = x / 0  # This will raise a ZeroDivisionError
    return b


# Run examples
if __name__ == "__main__":
    print("\nTesting calculate_sum:")
    show_traced_execution(calculate_sum, 5, 3)

    print("\nTesting process_numbers:")
    show_traced_execution(process_numbers, [1, 5, 2, 8, 3], 4)

    print("\nTesting analyze_data:")
    sample_data = {'a': 10, 'b': 20, 'c': 'string', 'd': 30}
    show_traced_execution(analyze_data, sample_data)

    print("\nTesting failing_function:")
    show_traced_execution(failing_function, 5)