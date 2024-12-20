import sys
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TraceEntry:
    line_no: int
    event: str
    changes: Dict[str, list]
    indent: int
    example_id: int
    return_value: Any = None


class ValueTracer:
    def __init__(self, example_id: int, source_lines: List[str], first_line_no: int):
        self.traces = []
        self.func_first_line = first_line_no
        self.error = None
        self.value_sequences = defaultdict(list)
        self.line_operations = set()
        self.example_id = example_id
        self.source_lines = source_lines

    def trace_function(self, frame, event, arg):
        line_no = frame.f_lineno

        if event in ('line', 'return'):
            current_locals = {
                k: v for k, v in frame.f_locals.items()
                if not k.startswith('__')
            }

            relative_line = line_no - self.func_first_line
            if 0 <= relative_line < len(self.source_lines):
                current_line = self.source_lines[relative_line]
                indent = len(current_line) - len(current_line.lstrip())

                # Track changes in variables
                for name, value in current_locals.items():
                    if name in current_line.strip():
                        if not current_line.strip().startswith('for'):
                            if '+=' in current_line:
                                self.line_operations.add((line_no, name))
                                last_values = self.value_sequences[(line_no, name)]
                                if not last_values or last_values[-1] != value:
                                    self.value_sequences[(line_no, name)].append(value)
                            elif '=' in current_line:
                                if not any((line, name) in self.line_operations for line in range(line_no)):
                                    self.line_operations.add((line_no, name))
                                    self.value_sequences[(line_no, name)] = [value]
                                elif name in current_line.split('=')[0].strip():
                                    last_values = self.value_sequences[(line_no, name)]
                                    if not last_values or last_values[-1] != value:
                                        self.value_sequences[(line_no, name)].append(value)

                        # Handle print statements
                        if 'print' in current_line:
                            self.line_operations.add((line_no, 'stdout'))
                            self.value_sequences[(line_no, 'stdout')].append(str(value))

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
                        example_id=self.example_id,
                        return_value=arg if event == 'return' else None
                    )
                    self.traces.append(trace)

        return self.trace_function


def format_value(v):
    if isinstance(v, (int, float, bool)):
        return str(v)
    return repr(v)


def extract_examples(source: str) -> Tuple[str, List[str]]:
    """Extract function definition and example calls from source code.

    More flexible extraction that:
    1. Recognizes direct function calls
    2. Handles assignments of function results
    3. Accepts print statements with function calls
    4. Still supports explicit '# Example' markers
    """
    lines = source.split('\n')

    # Find the end of the function definition
    func_end = 0
    in_function = False
    indent_level = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Check for function definition
        if stripped.startswith('def '):
            in_function = True
            # Get the base indentation level
            indent_level = len(line) - len(line.lstrip())
            continue

        if in_function:
            # Check if we're out of the function based on indentation
            if stripped and not line.startswith(' ' * (indent_level + 4)):
                func_end = i
                break

    # If no clear end found, try to find first function call
    if func_end == 0:
        func_name = None
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                func_name = line.split('def ')[1].split('(')[0].strip()
            elif func_name and func_name in line and '=' in line or 'print' in line or func_name + '(' in line:
                func_end = i
                break

    # If still no end found, assume whole source is function
    if func_end == 0:
        return source, []

    # Split function definition and examples
    func_lines = lines[:func_end]
    example_section = lines[func_end:]

    # Extract function name for identifying calls
    func_name = None
    for line in func_lines:
        if line.strip().startswith('def '):
            func_name = line.split('def ')[1].split('(')[0].strip()
            break

    if not func_name:
        return '\n'.join(func_lines), []

    # Process examples - both marked and unmarked
    example_blocks = []
    current_block = []
    in_marked_example = False

    for line in example_section:
        stripped = line.strip()

        # Skip empty lines unless in a marked example
        if not stripped and not in_marked_example:
            continue

        # Handle explicit example markers
        if stripped.startswith('# Example'):
            if current_block:
                example_blocks.append('\n'.join(current_block))
                current_block = []
            in_marked_example = True
            continue

        # Check for function calls in various forms
        is_func_call = (
                func_name + '(' in stripped or  # Direct call
                'print' in stripped and func_name in stripped or  # Print statement
                '=' in stripped and func_name in stripped  # Assignment
        )

        if is_func_call:
            if not in_marked_example:
                # Start a new unmarked example block
                if current_block:
                    example_blocks.append('\n'.join(current_block))
                    current_block = []
            current_block.append(stripped)
        elif in_marked_example and stripped:
            current_block.append(stripped)

    # Add final block if exists
    if current_block:
        example_blocks.append('\n'.join(current_block))

    return '\n'.join(func_lines), example_blocks


def get_function_from_string(source_code: str):
    """Convert source code string to a function object."""
    namespace = {}
    namespace['__builtins__'] = __builtins__
    try:
        exec(source_code, namespace)
        func_objects = [(name, obj) for name, obj in namespace.items()
                        if callable(obj) and not name.startswith('__')]
        if not func_objects:
            raise ValueError("No function found in the provided code")
        return func_objects[0][1]
    except Exception as e:
        raise ValueError(f"Error creating function from string: {str(e)}\nCode:\n{source_code}")


def execute_example(example_code: str, func, example_id: int, source_lines: List[str], first_line_no: int):
    """Execute an example and return its tracer.

    Args:
        example_code: The example code to execute
        func: The function object to trace
        example_id: Identifier for this example
        source_lines: Original source code lines
        first_line_no: Starting line number of the function

    Returns:
        ValueTracer object containing execution trace
    """
    # Set up the namespace with the function
    namespace = {'func': func}

    # Create tracer for this example
    tracer = ValueTracer(example_id, source_lines, first_line_no)

    # Set up the trace
    sys.settrace(tracer.trace_function)

    try:
        # Get function name from source lines
        func_name = None
        for line in source_lines:
            stripped = line.strip()
            if stripped.startswith('def '):
                func_name = stripped.split('def ')[1].split('(')[0].strip()
                break

        # Prepare the example code
        if func_name:
            # Replace all occurrences of the original function name
            modified_code = example_code.replace(func_name, 'func')

            # Handle both print and direct call cases
            if 'print(' in modified_code:
                # Ensure print is available in namespace
                namespace['print'] = print

            # Execute the modified code
            exec(modified_code, namespace)
        else:
            # If no function name found, execute as-is
            exec(example_code, namespace)

    except Exception as e:
        # Store any errors that occur during execution
        tracer.error = e
    finally:
        # Always restore the original trace function
        sys.settrace(None)

    return tracer


def show_traced_execution(source_code: str, print_output=True) -> str:
    """
    Show traced execution of a function with examples, accepting a string containing
    both function definition and example calls.
    """
    # Extract function and examples
    func_source, examples = extract_examples(source_code)
    func = get_function_from_string(func_source)

    # Get source lines
    source_lines = func_source.splitlines()
    first_line_no = 1  # Since we're using string source, we start at line 1

    # Execute each example and collect tracers
    tracers = []
    for i, example in enumerate(examples, 1):
        tracer = execute_example(example, func, i, source_lines, first_line_no)
        tracers.append(tracer)

    # Find maximum line length
    max_line_length = max(len(line.rstrip()) for line in source_lines)
    comment_position = max_line_length + 4

    # Process function lines
    output_lines = []
    for i, line in enumerate(source_lines):
        line_stripped = line.rstrip()
        current_line = line_stripped

        # Collect all traces for this line
        all_changes = defaultdict(list)
        returns = []

        for tracer_idx, tracer in enumerate(tracers, 1):
            for trace in tracer.traces:
                relative_line = trace.line_no - first_line_no
                if relative_line == i:
                    # Add changes with example number
                    for name, values in trace.changes.items():
                        if len(values) > 0 and (trace.line_no, name) in tracer.line_operations:
                            if name == 'stdout':
                                all_changes['stdout'].append((tracer_idx, values[-1]))
                            else:
                                all_changes[name].append((tracer_idx, values[-1]))
                    if trace.return_value is not None:
                        returns.append((tracer_idx, trace.return_value))

        # Format the line with all changes
        if all_changes or returns:
            spaces_needed = comment_position - len(line_stripped)
            if spaces_needed < 4:
                spaces_needed = 4
            padding = " " * spaces_needed

            changes = []
            # Format each type of change
            for name, values in sorted(all_changes.items()):
                if name == 'stdout':
                    changes.extend(f"Example {ex_id}: stdout={format_value(val)}"
                                   for ex_id, val in values)
                else:
                    changes.extend(f"Example {ex_id}: {name}={format_value(val)}"
                                   for ex_id, val in values)

            if returns:
                changes.extend(f"Example {ex_id}: returns {format_value(val)}"
                               for ex_id, val in returns)

            if changes:
                current_line += f"{padding}# → {', '.join(changes)}"

        output_lines.append(current_line)
        if print_output:
            print(current_line)

    # Add example executions
    for i, example in enumerate(examples, 1):
        output_lines.extend(['', f'# Example {i}', example])
        tracer = tracers[i - 1]
        if tracer.error:
            output_lines.append(f"# → Error: {type(tracer.error).__name__}: {str(tracer.error)}")
        else:
            # Find the return value from the last trace
            for trace in reversed(tracer.traces):
                if trace.return_value is not None:
                    output_lines[-1] += f"  # → returns {format_value(trace.return_value)}"
                    break

    if print_output:
        print("\n".join(output_lines[len(source_lines):]))

    return "\n".join(output_lines)


# Test the implementation
if __name__ == "__main__":
    test_code = """
import json

def validate_request_format(request_data):
    try:
        # Step 1: Parse JSON Data
        data = json.loads(request_data)
        
        # Debugging print to show parsed data
        print("Parsed JSON Data:", data)
        
        # Step 2: Validate Required Fields
        required_fields = ['email', 'age', 'subscription_tier', 'user_data']
        for field in required_fields:
            if field not in data or data[field] is None:
                return (False, f"400: Missing or null field '{field}'")
        
        # Debugging print to show all required fields are present
        print("All required fields are present and not null.")
        
        # Step 3: Validate Data Types
        if not isinstance(data['email'], str):
            return (False, "422: 'email' must be a string")
        if not isinstance(data['age'], int):
            return (False, "422: 'age' must be an integer")
        if not isinstance(data['subscription_tier'], str):
            return (False, "422: 'subscription_tier' must be a string")
        if not isinstance(data['user_data'], dict):
            return (False, "422: 'user_data' must be a dictionary")
        
        # Debugging print to show all data types are valid
        print("All data types are valid.")
        
        # Step 4: Return Result
        return (True, "")
    
    except json.JSONDecodeError:
        # Step 1.1: Handle Malformed JSON
        return (False, "400: Malformed JSON")

# Example usage:
request_data = '{"email": "test@example.com", "age": 30, "subscription_tier": "basic", "user_data": {}}'
print(validate_request_format(request_data))
            """

    print("\nTesting with example annotations:")
    annotated_code = show_traced_execution(test_code)

"""
ISSUE ANALYSIS FROM CLAUDE:
Let me analyze this step by step, focusing on what appears to be mixed up in the traced execution output:

1. First Trace Issue:
The line `required_fields = ['email', 'age', 'subscription_tier', 'user_data']` shows:
```python
# → Example 1: data={'email': 'test@example.com', 'age': 30, 'subscription_tier': 'basic', 'user_data': {}}
```
This seems incorrect because it's tracking `data` on a line where `data` isn't being modified. Looking at the code, I can see this is happening because of how the tracer works - it's showing variables that appear in the line, not necessarily ones being modified on that line.

2. Print Statement Issue:
The line `print("All required fields are present and not null.")` shows:
```python
# → Example 1: stdout='user_data'
```
This appears incorrect because the actual output should be the message "All required fields are present and not null." The issue here seems to be in the trace collection logic - it's possibly capturing the last value being processed (the last field from required_fields) instead of the actual print output.

3. Looking at the Source Code:
In the `ValueTracer` class, there's logic that tracks changes when a variable name appears in the current line. The issue appears to be that it's not properly distinguishing between:
- Variables being read
- Variables being written to
- Print statement outputs

The root cause appears to be in this part of the tracer's logic:
```python
if name in current_line.strip():
    if not current_line.strip().startswith('for'):
```
This is too broad - it's capturing any variable that appears in the line, not just ones being assigned or modified. For print statements, it's also not properly capturing the full output, instead sometimes capturing other variables that happen to be in scope.

The solution would likely involve:
1. Being more precise about when to track variable changes (only on actual assignments)
2. Better handling of print statement outputs (capturing the full print output)
3. Distinguishing between variable reads and writes
"""