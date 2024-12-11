def _setup_venv(self):
    """Set up a virtual environment for code execution."""
    self.project_dir = tempfile.mkdtemp()
    self.venv_path = os.path.join(self.project_dir, 'venv')

    try:
        venv.create(self.venv_path, with_pip=True)
    except Exception as e:
        self._cleanup_venv()
        raise RuntimeError(f"Failed to create virtual environment: {e}")


def _cleanup_venv(self):
    """Clean up the virtual environment."""
    if self.project_dir and os.path.exists(self.project_dir):
        try:
            import shutil
            shutil.rmtree(self.project_dir)
            self.project_dir = None
            self.venv_path = None
        except Exception as e:
            print(f"Error cleaning up environment: {e}")


def _execute_in_venv(self, code: str) -> tuple[int, str, str]:
    """Execute code in virtual environment and capture stdout."""
    if not self.venv_path:
        self._setup_venv()

    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name

        python_path = os.path.join(self.venv_path, 'Scripts', 'python.exe') if os.name == 'nt' \
            else os.path.join(self.venv_path, 'bin', 'python')

        result = subprocess.run(
            [python_path, temp_file],
            capture_output=True,
            text=True,
            timeout=2
        )

        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        return 1, "", "Code execution timed out"
    except Exception as e:
        return 1, "", str(e)
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception:
                pass

