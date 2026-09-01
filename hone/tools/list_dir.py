import os

from ..sandbox import SandboxEscape, resolve_in_sandbox

schema_get_files_info = {
    "type": "function",
    "function": {
        "name": "get_files_info",
        "description": "Lists files in a specified directory relative to the working directory, providing file size and directory status",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory path to list files from, relative to the working directory (default is the working directory itself)",
                },
            },
        },
    },
}

def get_files_info(working_directory: str, directory: str = ".") -> str:
    try:
        try:
            target_dir = resolve_in_sandbox(working_directory, directory)
        except SandboxEscape:
            return f'Error: Cannot list "{directory}" as it is outside the permitted working directory'

        if not os.path.isdir(target_dir):
            return f'Error: "{directory}" is not a directory'

        items_in_target_dir = os.listdir(target_dir)
        files_info: list[str] = []
        for item in items_in_target_dir:
            filepath = os.path.join(target_dir,item)
            file_size = os.path.getsize(filepath)
            is_dir = os.path.isdir(filepath)
            files_info.append(f" - {item}: file_size={file_size} bytes, is_dir={is_dir}")

        label = "current" if directory == "." else f'"{directory}"'
        return f"Result for {label} directory:\n" + "\n".join(files_info)

    except Exception as e:
        return f'Error: {e}'
