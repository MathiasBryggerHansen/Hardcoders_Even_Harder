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

import subprocess
import pickle
import yaml
import tempfile
import os


def process_user_data(user_input, filename):
    """
    This function contains several security vulnerabilities that Bandit would detect:
    - Command injection vulnerability
    - Unsafe deserialization
    - Unsafe YAML loading
    - Insecure temp file creation
    - Hardcoded password
    """
    # B603: subprocess call with shell=True
    subprocess.Popen(f"echo {user_input}", shell=True)

    # B301: Pickle and its variants can be unsafe when used to deserialize untrusted data
    with open(filename, 'rb') as f:
        data = pickle.load(f)

    # B506: Use of unsafe yaml load
    config = yaml.load("""
        server: localhost
        port: 8080
        password: hardcoded_secret123
    """)

    # B108: Probable insecure usage of temp file/directory
    temp = tempfile.mktemp()
    with open(temp, 'w') as f:
        f.write(user_input)

    # B105: Hardcoded password string
    db_password = "super_secret_password123"

    # B601: Possible shell injection via Paramiko
    os.system(f"cat {filename}")

    # B307: Use of eval
    result = eval(user_input)

    return data, config, result

# Usage (DO NOT USE IN PRODUCTION):
# process_user_data("malicious_input", "untrusted.pkl")
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
