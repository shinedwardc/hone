import os
import subprocess
import sys

from ..sandbox import SandboxEscape, resolve_in_sandbox

TIMEOUT_SECONDS = 30

schema_run_python_file = {
    "type": "function",
    "function": {
        "name": "run_python_file",
        "description": (
            "Run a Python file with the working directory as its cwd. Returns the exit "
            "code when nonzero, plus STDOUT and STDERR. Times out after "
            f"{TIMEOUT_SECONDS} seconds."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path of the Python file to run, relative to the working directory."
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command-line arguments passed to the file, as a list of strings.",
                },
            },
            "required": ["file_path"],
        },
    },
}

def run_python_file(
    working_directory: str, file_path: str, args: list[str] | None = None
) -> str:
    try:
        abs_working_directory = os.path.realpath(working_directory)
        try:
            target_file_path = resolve_in_sandbox(working_directory, file_path)
        except SandboxEscape:
            return f'Error: Cannot execute "{file_path}" as it is outside the permitted working directory'
        if not os.path.isfile(target_file_path):
            return f'Error: "{file_path}" does not exist or is not a regular file'
        if not file_path.endswith('.py'):
            return f'Error: "{file_path}" is not a Python file'

        command = [sys.executable, target_file_path]
        if args:
            command.extend(args)

        process = subprocess.run(
            command,
            cwd=abs_working_directory,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS
        )

        output: list[str] = []
        if process.returncode:
            output.append(f"Process exited with code {process.returncode}")

        if not process.stdout and not process.stderr:
            output.append("No output produced")
        if process.stdout:
            output.append(f"STDOUT: {process.stdout}")
        if process.stderr:
            output.append(f"STDERR: {process.stderr}")

        return "\n".join(output)

    except Exception as e:
        return f'Error: executing Python file: {e}'