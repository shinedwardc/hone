import os

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
        working_dir_abs = os.path.abspath(working_directory) # e.g. work_directory="calculator" => returns "/home/steve/ai-agent/calculator"
        target_dir = os.path.normpath(os.path.join(working_dir_abs, directory))
        valid_target_dir = os.path.commonpath([working_dir_abs,target_dir]) == working_dir_abs
        result_string = "Result for current directory:\n"

        if not os.path.isdir(target_dir):
            return result_string + f"{directory} is not a directory"
        
        if not valid_target_dir:
            return result_string + f'   Error: Cannot list "{directory}" as it is outside the permitted working directory'
    
        items_in_target_dir = os.listdir(target_dir)
        files_info: list[str] = []
        for item in items_in_target_dir:
            filepath = os.path.join(target_dir,item)
            file_size = os.path.getsize(filepath)
            is_dir = os.path.isdir(filepath)
            files_info.append(f" - {item}: file_size={file_size} bytes, is_dir={is_dir}")
        return result_string + "\n".join(files_info)

    except Exception as e:
        return f'Error: {e}'