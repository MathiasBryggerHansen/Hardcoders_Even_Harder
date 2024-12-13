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

#TODO: follow the example. The final annotate_code should take the following:
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

