import os

from ..sandbox import SandboxEscape, resolve_in_sandbox

schema_write_file = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write or overwrite content to a specified file in directory",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path of the specified file to write on",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write or overwrite on to the file",
                },
            },
            "required": ["file_path", "content"],
        },
    },
}

def write_file(working_directory: str, file_path: str, content: str) -> str:
    try:
        try:
            target_file_path = resolve_in_sandbox(working_directory, file_path)
        except SandboxEscape:
            return f'Error: Cannot write to "{file_path}" as it is outside the permitted working directory'

        if os.path.isdir(target_file_path):
            return f'Error: Cannot write to "{file_path}" as it is a directory'

        os.makedirs(os.path.dirname(target_file_path), exist_ok=True)

        with open(target_file_path, "w") as file:
            file.write(content)

        return f'Successfully wrote to "{file_path}" ({len(content)} characters written)'

    except Exception as e:
        return f'Error: {e}'
