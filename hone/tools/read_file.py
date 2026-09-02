import os

from ..sandbox import SandboxEscape, resolve_in_sandbox

MAX_CHARS = 10000

schema_get_file_content = {
    "type": "function",
    "function": {
        "name": "get_file_content",
        "description": (
            "Return the text content of a file. Truncated at "
            f"{MAX_CHARS} characters with a marker at the cut; a truncated read is not "
            "the whole file, so do not draw conclusions about code you have not seen."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path of the file to read, relative to the working directory."
                },
            },
            "required": ["file_path"]
        }
    }
}

def get_file_content(working_directory: str, file_path: str) -> str:
    try:
        try:
            target_file_path = resolve_in_sandbox(working_directory, file_path)
        except SandboxEscape:
            return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'
        
        if not os.path.isfile(target_file_path):
            return f'Error: File not found or is not a regular file: "{file_path}"'

        with open(target_file_path, "r", encoding="utf-8") as file:
            content = file.read(MAX_CHARS)
            if file.read(1):
                content += f'[...File "{file_path}" truncated at {MAX_CHARS} characters]'

        return content

    except Exception as e:
        return f"Error: {e}"
