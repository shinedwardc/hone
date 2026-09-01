import os
from dotenv import load_dotenv
import argparse 
from openai import OpenAI
import json
from prompts import system_prompt
from call_function import available_functions, call_function

def main() -> None:
    parser = argparse.ArgumentParser(description="User message for openrouter")
    parser.add_argument("user_prompt", type=str, help="User prompt")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key is None:
        raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": args.user_prompt},
    ]

    for _ in range(20):

        response = client.chat.completions.create(
            model="openrouter/free",
            messages=messages,
            #temperature=0,
            tools=available_functions,
        )

        if not response.usage:
            raise RuntimeError("Failed openrouter API request")

        if args.verbose:
            print(f"User prompt: {args.user_prompt}")
            print(f"Prompt tokens: {response.usage.prompt_tokens}")
            print(f"Response tokens: {response.usage.completion_tokens}")

        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            print("Response:")
            print(message.content)
            break

        
        for tool_call in message.tool_calls:
            if tool_call.type != "function":
                continue
            # function_args = json.loads(tool_call.function.arguments or "{}")
            # print(f"Caling function: {tool_call.function.name}({function_args})")
            result_message = call_function(tool_call,args.verbose)
            if not result_message["content"]:
                raise Exception("Tool message should have a non-empty 'content'")
            if args.verbose:
                print(f"-> {result_message["content"]}")
            messages.append(result_message)
    
    else:
        print("Model requesting too many calls over the limit of 20")
        exit(1)

    return

if __name__ == "__main__":
    main()
