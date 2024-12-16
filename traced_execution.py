import sys
from io import StringIO
import traceback
import inspect
import copy


def analyze_trace(func_str):
    """
    Analyzes the execution trace of a function string and returns a dictionary
    containing progressive variable values at each line number where they change,
    including any errors that occur during execution.
    """
    variables = {}
    old_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = captured_output

    try:
        source_lines = func_str.strip().split('\n')
        real_lines = {}
        current_real_line = 1

        for i, line in enumerate(source_lines, 1):
            if line.strip():
                real_lines[i] = current_real_line
                current_real_line += 1

        namespace = {}
        exec(func_str, namespace)

        functions = {}
        for name, obj in namespace.items():
            if inspect.isfunction(obj):
                for i, line in enumerate(source_lines, 1):
                    if line.strip().startswith(f'def {name}'):
                        functions[name] = real_lines[i]
                        break

        main_func_name = None
        for name in functions:
            if 'test' in name.lower():
                main_func_name = name
                break

        if main_func_name is None:
            raise ValueError("No test function found")

        progressive_variables = {}
        last_values = {}
        function_offsets = {}
        stdout_lines = {}
        error_info = {}
        current_print_line = None

        def custom_write(text):
            if current_print_line is not None and text.strip():
                stdout_line = current_print_line + 1
                if stdout_line not in stdout_lines:
                    stdout_lines[stdout_line] = []
                stdout_lines[stdout_line].append(text.strip())
            captured_output.write(text)

        class TracedStringIO(StringIO):
            def write(self, text):
                custom_write(text)

        def safe_copy(value):
            try:
                return copy.deepcopy(value)
            except:
                try:
                    return copy.copy(value)
                except:
                    return value

        def calculate_real_line(frame, func_name):
            if func_name not in function_offsets:
                function_offsets[func_name] = frame.f_lineno

            offset = frame.f_lineno - function_offsets[func_name]
            return functions[func_name] + offset

        def tracer(frame, event, arg):
            try:
                if event == 'line':
                    func_name = frame.f_code.co_name
                    if func_name not in functions:
                        return tracer

                    nonlocal current_print_line
                    line_num = calculate_real_line(frame, func_name)
                    current_print_line = line_num

                    for var_name, var_value in frame.f_locals.items():
                        if var_name.startswith('__'):
                            continue

                        try:
                            current_value = safe_copy(var_value)
                            qualified_name = f"{func_name}_{var_name}" if func_name != main_func_name else var_name

                            if qualified_name not in progressive_variables:
                                progressive_variables[qualified_name] = {}
                                last_values[qualified_name] = None

                            if current_value != last_values[qualified_name]:
                                if line_num not in progressive_variables[qualified_name]:
                                    progressive_variables[qualified_name] = {}

                                if line_num not in progressive_variables[qualified_name]:
                                    progressive_variables[qualified_name][line_num] = []

                                if not progressive_variables[qualified_name][line_num] or \
                                        progressive_variables[qualified_name][line_num][-1] != current_value:
                                    progressive_variables[qualified_name][line_num].append(current_value)
                                    last_values[qualified_name] = current_value
                        except Exception as e:
                            continue

                    sys.stdout = TracedStringIO()
                elif event == 'exception':
                    exc_type, exc_value, exc_traceback = arg
                    func_name = frame.f_code.co_name
                    if func_name not in functions:
                        return tracer

                    line_num = calculate_real_line(frame, func_name)
                    error_info[line_num] = f"{exc_type.__name__}: {str(exc_value)}"

            except Exception as e:
                pass

            return tracer

        sys.settrace(tracer)
        try:
            namespace[main_func_name]()
        except Exception as e:
            pass
        finally:
            sys.settrace(None)

        if stdout_lines:
            progressive_variables['stdout'] = stdout_lines

        if error_info:
            progressive_variables['errors'] = error_info

        return progressive_variables

    finally:
        sys.stdout = old_stdout


def annotate_code(func_str):
    """
    Takes a function string and returns an annotated version showing variable states at each line.

    Args:
        func_str (str): The function code to analyze and annotate

    Returns:
        str: The annotated code with variable states as comments
    """
    # Get trace analysis
    trace_result = analyze_trace(func_str)

    # Split the code into lines and strip right whitespace
    lines = [line.rstrip() for line in func_str.splitlines()]

    # Find the maximum line length for alignment
    max_line_length = max(len(line) for line in lines)

    # Process each line
    annotated_lines = []
    for i, line in enumerate(lines, 1):
        # Start with the original line
        annotated_line = line

        # Collect all variable states for this line
        var_states = []
        for var_name, line_states in trace_result.items():
            if var_name == 'stdout' or var_name == 'errors':
                continue
            if i in line_states:
                # Get the last (most recent) value for this variable at this line
                last_value = line_states[i][-1]
                var_states.append(f"{var_name} = {repr(last_value)}")

        # Add stdout if present
        if 'stdout' in trace_result and i in trace_result['stdout']:
            outputs = trace_result['stdout'][i]
            var_states.append(f"output: {repr(outputs)}")

        # Add error if present
        if 'errors' in trace_result and i in trace_result['errors']:
            var_states.append(f"error: {trace_result['errors'][i]}")

        # If we have states to annotate, add them as a comment
        if var_states:
            # Pad the line with spaces to align comments
            padding = " " * (max_line_length - len(line))
            states_str = ", ".join(var_states)
            annotated_line = f"{line}{padding}  # {states_str}"

        annotated_lines.append(annotated_line)

    return "\n".join(annotated_lines)


def test_annotator():
    test_func = """
def test_function():
    x = 0
    y = []

    # First operation - should work
    y.append(x + 1)

    # Second operation - should raise ValueError
    int('not a number')

    # This line shouldn't execute
    y.append(x + 2)
    """
    print(analyze_trace(test_func))
    #annotated = annotate_code(test_func)
    print("Annotated code:")
    # print(annotated)


if __name__ == "__main__":

    test_annotator()

import sys
import dis
import pandas as pd
from datetime import datetime
from io import StringIO
from contextlib import contextmanager


class VariableTracer:
    def __init__(self):
        self.trace_data = []
        self.previous_vars = {}
        self.stdout_buffer = StringIO()
        self.base_line = None
        self.in_loop = False
        self.loop_vars = set()
        self.loop_start_line = None

    @contextmanager
    def capture_stdout(self):
        old_stdout = sys.stdout
        sys.stdout = self.stdout_buffer
        try:
            yield
        finally:
            sys.stdout = old_stdout

    def detect_loop_start(self, frame):
        """Detect if we're at the start of a loop and identify loop variables"""
        instructions = list(dis.get_instructions(frame.f_code))
        current_offset = frame.f_lasti

        # Find the current instruction
        current_instr = None
        for i, instr in enumerate(instructions):
            if instr.offset == current_offset:
                current_instr = instr
                break

        if current_instr:
            # Check for both FOR_ITER and SETUP_LOOP (while loops)
            is_loop_start = (
                    current_instr.opname == 'FOR_ITER' or  # for loops
                    (current_instr.opname in ('POP_JUMP_IF_FALSE', 'POP_JUMP_IF_TRUE') and  # while loops
                     i > 0 and instructions[i - 1].opname == 'GET_ITER')
            )

            if is_loop_start:
                self.in_loop = True
                self.loop_start_line = frame.f_lineno
                # Compare with previous state to find new variables
                new_vars = set(frame.f_locals.keys()) - set(self.previous_vars.keys())
                self.loop_vars.update(new_vars)
                return True
        return False

    def trace_function(self, frame, event, arg):
        if event == 'call':
            self.base_line = frame.f_lineno

        if event in ['call', 'return', 'exception', 'line']:
            current_vars = frame.f_locals.copy()
            # Add 1 to the line number specifically for return events
            line_adjustment = 1 if event == 'return' else 0
            relative_line = frame.f_lineno - self.base_line + line_adjustment

            # Check for loop start
            if event == 'line':
                is_loop_start = self.detect_loop_start(frame)
                if is_loop_start and self.loop_vars:
                    # Move loop variables to previous line's trace
                    if self.trace_data:
                        for var in self.loop_vars:
                            if var in current_vars:
                                self.trace_data[-1]['vars'][var] = current_vars[var]

            # Get current stdout
            stdout_content = self.stdout_buffer.getvalue()
            if stdout_content:
                self.stdout_buffer.truncate(0)
                self.stdout_buffer.seek(0)

            extra_info = None
            if event == 'return':
                extra_info = f"returned: {arg}"
                current_vars['return_value'] = arg
            elif event == 'exception':
                extra_info = f"exception: {arg[0].__name__}: {arg[1]}"

            self.trace_data.append({
                'timestamp': datetime.now().strftime('%H:%M:%S.%f'),
                'line': relative_line,
                'event': event,
                'stdout': stdout_content if stdout_content else None,
                'extra_info': extra_info,
                'vars': current_vars.copy()
            })

            self.previous_vars = current_vars

        return self.trace_function

    def get_trace_df(self):
        df = pd.DataFrame(self.trace_data)
        var_df = pd.json_normalize(df['vars'])
        return pd.concat([df.drop('vars', axis=1), var_df], axis=1)


def trace_variables(code_string, *args, **kwargs):
    # Extract the function definition and parameters from the code string
    import re
    match = re.match(r'def\s+(\w+)\s*\((.*?)\):', code_string)
    if not match:
        raise ValueError("Code string must start with a function definition")

    func_name, params = match.groups()

    # Create the function with the original parameters
    namespace = {}
    exec(code_string, globals(), namespace)
    traced_function = namespace[func_name]

    # Use the existing tracing mechanism
    tracer = VariableTracer()
    with tracer.capture_stdout():
        sys.settrace(tracer.trace_function)
        try:
            result = traced_function(*args, **kwargs)
        except Exception as e:
            result = f"Error: {str(e)}"
        finally:
            sys.settrace(None)
    return tracer.get_trace_df(), result




# Example usage:
code = """def example(x):
    a = x * 2
    print(f"a is {a}")

    for i in range(3):
        print(f"i is {i}")

    total = 0
    for j in range(2):
        total += j
        print(f"total is {total}")

    return total"""

trace_df, result = trace_variables(code, 5)
#annotated_code = annotate_code_with_traces(code, trace_df)
print(trace_df)


def get_variable_changes(trace_df):
    """
    Analyzes the trace DataFrame and creates a new DataFrame where each variable
    is represented as a tuple (value, changed_from_previous).

    Args:
        trace_df (pd.DataFrame): The trace DataFrame from VariableTracer

    Returns:
        pd.DataFrame: A new DataFrame with tuples indicating value and change status
    """
    # Create a copy of the DataFrame to avoid modifying the original
    result_df = trace_df.copy()

    # Get all variable columns (exclude metadata columns)
    metadata_cols = ['timestamp', 'line', 'event', 'stdout', 'extra_info']
    var_cols = [col for col in trace_df.columns if col not in metadata_cols]

    # For each variable column, create a new column with tuples
    for col in var_cols:
        # Create a series of booleans indicating if the value changed
        changed = trace_df[col] != trace_df[col].shift()
        # First row should be marked as changed since it's the initial value
        changed.iloc[0] = True

        # Create tuples of (value, changed)
        result_df[col] = list(zip(trace_df[col], changed))

    return result_df


def get_variable_changes(trace_df):
    """
    Analyzes the trace DataFrame and creates a new DataFrame where each variable
    is accompanied by a boolean column indicating if it changed from the previous line.
    Handles NaN values appropriately and only marks initial non-NaN values as changed.

    Args:
        trace_df (pd.DataFrame): The trace DataFrame from VariableTracer

    Returns:
        pd.DataFrame: A new DataFrame with original values and change indicators
    """
    # Create a copy of the DataFrame to avoid modifying the original
    result_df = trace_df.copy()

    # Get all variable columns (exclude metadata columns)
    metadata_cols = ['timestamp', 'line', 'event', 'stdout', 'extra_info']
    var_cols = [col for col in trace_df.columns if col not in metadata_cols]

    # For each variable column, create a new column indicating changes
    for col in var_cols:
        # Create a boolean column indicating if the value changed
        change_col = f"{col}_changed"

        # Use pd.isna() to handle NaN values properly
        current_values = trace_df[col]
        previous_values = trace_df[col].shift()

        # Compare values, handling NaN properly
        is_changed = ~((current_values.isna() & previous_values.isna()) |
                       (current_values == previous_values))

        result_df[change_col] = is_changed

        # First row should only be marked as changed if it's not NaN
        result_df.loc[result_df.index[0], change_col] = not pd.isna(current_values.iloc[0])

    return result_df


def annotate_code_with_changes(code_string, changes_df):
    """
    Annotates code with lists of values that variables take and stdout content.

    Args:
        code_string (str): The original code as a string
        changes_df (pd.DataFrame): DataFrame with _changed columns from get_variable_changes()
    """
    code_lines = code_string.split('\n')
    annotated_lines = []

    # Get variable columns (excluding metadata and _changed columns)
    metadata_cols = {'timestamp', 'line', 'event', 'stdout', 'extra_info'}
    var_cols = {col for col in changes_df.columns
                if not col.endswith('_changed')
                and col not in metadata_cols}

    # Track when variables are first assigned
    first_assignment = set()

    # Process each line
    for i, line in enumerate(code_lines):
        current_line = line.rstrip()
        next_line_data = changes_df[changes_df['line'] == i + 1]
        current_line_data = changes_df[changes_df['line'] == i]

        annotations = []

        # Handle variable changes
        if not next_line_data.empty:
            for var in var_cols:
                # Special case for function parameters (use current line)
                line_data = current_line_data if 'def' in line and var in line else next_line_data

                # Check if this is an initial assignment
                if '=' in line and var in line.split('=')[0] and var not in first_assignment:
                    first_assignment.add(var)
                    if f"{var}_changed" in changes_df.columns and line_data[f"{var}_changed"].any():
                        values = [line_data[var].iloc[0]]  # Just take the first value
                        if pd.notna(values[0]):
                            annotations.append(f"{var} = [{values[0]}]")
                # Regular variable change
                elif f"{var}_changed" in changes_df.columns and line_data[f"{var}_changed"].any():
                    values = line_data[var].dropna().unique()
                    if len(values) > 0 and var in line:
                        annotations.append(f"{var} = [{', '.join(str(v) for v in values)}]")

        # Add the current line with any variable annotations
        if annotations:
            current_line += "  # " + ", ".join(annotations)
        annotated_lines.append(current_line)

        # Add stdout if print statement
        stdout_data = changes_df[changes_df['line'] == i + 1]
        if 'print' in line and changes_df['line'].eq(i - 1).any():
            stdout = changes_df[changes_df['line'].eq(i - 1)]['stdout'].iloc[0]
            if pd.notna(stdout):
                indent = len(line) - len(line.lstrip())
                cleaned_stdout = stdout.strip().replace('\n', '')
                stdout_line = ' ' * indent + f"# stdout: {cleaned_stdout}"
                annotated_lines.append(stdout_line)

    return '\n'.join(annotated_lines)

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

# Option 2: Also set the width to avoid column wrapping
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

#print(get_variable_changes(trace_df))

changes_df = get_variable_changes(trace_df)


print(annotate_code_with_changes(code_string=code, changes_df=changes_df))

#print(changes_df)

#TODO: follow the example. The final annotate_code should take the following:
#Analyze trace is not working completely - look at trace
# """def test_function():
#     x = 0
#     numbers = [1, 2, 3]
#     for num in numbers:
#         x += num
#         print(x)"""
#and output:
# """def test_function():
#     x = 0  # x = 0
#     numbers = [1, 2, 3]  # numbers = [1, 2, 3]
#     for num in numbers:  # num = [1, 2, 3]
#         x += num  # x = [1, 3, 6]
#         print(x)  # stdout = [1, 3, 6]"""

