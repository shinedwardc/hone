import os
MAX_CHARS = 10000

schema_get_file_content = {
    "type": "function",
    "function": {
        "name": "get_file_content",
        "description": "Return file content from a specific file in directory",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "file_path": "string",
                    "description": "File path to retrieve content from"
                },
            },
            "required": ["file_path"]
        }
    }
}

def get_file_content(working_directory: str, file_path: str) -> str:
    try:
        abs_working_dir = os.path.abspath(working_directory)
        target_file_path = os.path.normpath(os.path.join(abs_working_dir, file_path))
        if not os.path.commonpath([abs_working_dir,target_file_path]) == abs_working_dir:
            return f'Error: Cannot read "{target_file_path} as it is outside the permitted working directory'
        if not os.path.isfile(target_file_path):
            return f'Error: File not found or is not a regular file: "{file_path}"'

        with open(target_file_path, "r", encoding="utf-8") as file:
            content = file.read(MAX_CHARS)
            if file.read(1):
                content += f'[...File "{file_path}" truncated at {MAX_CHARS} characters]'

        return content
    
    except Exception as e:
        return f"Error: {e}"