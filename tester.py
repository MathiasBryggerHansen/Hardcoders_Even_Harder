# import sys
# import tempfile
# import subprocess
# import json
# from pylint.lint import Run
# import os
# from pylint.reporters.text import TextReporter
# #
# #
# from pylint.lint import Run
# from pylint.reporters import BaseReporter
# from io import StringIO
#

def parse_message_string(message_str):
    content = message_str.strip()[8:-1]

    # Split by comma while respecting nested structures
    attributes = {}
    current_key = ""
    current_value = ""
    in_nested = 0

    for part in content.split("="):
        # Handle key
        if current_key == "":
            current_key = part.strip()
            continue

        # Handle value
        value_parts = part.split(",")
        if len(value_parts) > 1:
            current_value = value_parts[0].strip().strip("'")
            attributes[current_key] = current_value
            current_key = value_parts[-1].strip()
        else:
            attributes[current_key] = part.strip().strip("'")

    return attributes

# Example usage
message = """Message(msg_id='C0303', symbol='trailing-whitespace', msg='Trailing whitespace', C='C', category='convention', confidence=Confidence(name='HIGH', description='Warning that is not based on inference result.'), abspath='C:\\Users\\Lasse\\PycharmProjects\\Hardcoders_Even_Harder\\tmpvawjruin.py', path='tmpvawjruin.py', module='tmpvawjruin', obj='', line=3, column=0, end_line=None, end_column=None)"""

result = parse_message_string(message)
print(result)
# class CaptureReporter(BaseReporter):
#     def __init__(self):
#         super().__init__()
#         self.output = StringIO()
#
#     def handle_message(self, msg):
#         self.output.write(str(msg) + '\n')
#
#     def _display(self, layout):
#         pass
#
#
# def badcode(x):
#     global z
#
#
#     if x > 10:
#         if x > 20:
#             if x > 30:
#                 if x > 40:
#                     print("Nested conditions!")
#
#
# code = """
#
#
# global z
#
#
# if x > 10:
#     if x > 20:
#         if x > 30:
#             if x > 40:
#                 print("Nested conditions!")
#
# """
#
#
# def run_pylint(code):
#     with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8', dir=os.getcwd()) as temp_file:
#         temp_file.write(code)
#
#         temp_file.close()  # Explicitly close the file
#
#         temp_file_path = temp_file.name
#
#         reporter = CaptureReporter()
#         Run([temp_file_path], reporter=reporter,exit=False)
#         results = reporter.output.getvalue()
#
#         print(results)
#         #
#         # try:
#         #    Run([temp_file_path], exit=False, reporter=TextReporter(temp_file_path))
#         #    print(temp_file_path)
#         # finally:
#         #     # Clean up the temporary file
#         #     os.unlink(temp_file_path)
#
# run_pylint(code)
#
