import sys
import tempfile
import subprocess
import json
from pylint.lint import Run
import os
#
#
def badcode(x):
    global z


    if x > 10:
        if x > 20:
            if x > 30:
                if x > 40:
                    print("Nested conditions!")


code = """


global z


if x > 10:
    if x > 20:
        if x > 30:
            if x > 40:
                print("Nested conditions!")

"""


def run_pylint(code):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8', dir=os.getcwd()) as temp_file:
        temp_file.write(code)

        temp_file.close()  # Explicitly close the file

        temp_file_path = temp_file.name

        try:
           test = Run([temp_file_path])
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)

run_pylint(code)

