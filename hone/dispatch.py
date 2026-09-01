import json
from collections.abc import Callable
from functions import get_files_info
from functions import get_file_content
from functions import run_python_file
from functions import write_file

available_functions = [
    get_files_info.schema_get_files_info,
    get_file_content.schema_get_file_content,
    run_python_file.schema_run_python_file,
    write_file.schema_write_file,
]

def call_function(tool_call, verbose: bool = False) -> dict:

    function_name = tool_call.function.name
    raw_args = tool_call.function.arguments or "{}"

    try:
        function_args = json.loads(raw_args)
    except json.JSONDecodeError as e:
        if verbose:
            print(f" - Invalid arguments for {function_name}: {raw_args!r}")
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": (
                f"Error: arguments for {function_name} were not valid JSON ({e}). "
                "Resend the call with properly escaped JSON."
            ),
        }

    function_args["working_directory"] = "./calculator"

    if verbose:
        print(f" - Calling function: {function_name}({function_args})")
    else:
        print(f" - Calling function: {function_name}")

    function_map: dict[str, Callable[..., str]] = {
        "get_file_content": get_file_content.get_file_content,
        "get_files_info": get_files_info.get_files_info,
        "run_python_file": run_python_file.run_python_file,
        "write_file": write_file.write_file,
    }

    if function_name not in function_map:
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": f"Error: Unknown function: {function_name}",
        }

    try:
        result = function_map[function_name](**function_args)
    except TypeError as e:
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": f"Error: bad arguments for {function_name}: {e}",
        }

    return {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": result,
    }
