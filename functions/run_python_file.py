import os
import subprocess

schema_run_python_file = {
    "type": "function",
    "function": {
        "name": "run_python_file",
        "description": "Run the specified python file with arguments and returns output",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path of Python file to run"
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of optional arguments for the Python file to run with",
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
        abs_working_directory = os.path.abspath(working_directory)
        target_file_path = os.path.normpath(os.path.join(abs_working_directory,file_path))
        if not os.path.commonpath([abs_working_directory,target_file_path]) == abs_working_directory:
            return f'Error: Cannot execute "{file_path}" as it is outside the permitted working directory'
        if not os.path.isfile(target_file_path):
            return f'Error: "{file_path}" does not exist or is not a regular file'
        if not file_path.endswith('.py'):
            return f'Error: "{file_path}" is not a Python file'
        
        command = ["python", target_file_path]
        if args:
            command.extend(args)

        process = subprocess.run(
            command,
            cwd=abs_working_directory,
            capture_output=True,
            text=True,
            timeout=30
        )

        output: list[str] = []
        if process.returncode:
            output.append("Process exited with code X")

        if not process.stdout and not process.stderr:
            output.append("No output produced")
        if process.stdout:
            output.append(f"STDOUT: {process.stdout}")
        if process.stderr:
            output.append(f"STDERR: {process.stderr}")

        return "\n".join(output)

    except Exception as e:
        return f'Error: executing Python file: {e}'