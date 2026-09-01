import argparse
import os

from dotenv import load_dotenv
from openai import OpenAI

from .dispatch import available_functions, call_function
from .prompts import system_prompt

# Presets. Any of these fields can be overridden per-run by a flag or an env var.
PROVIDERS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "model": "openrouter/free",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1/",
        "api_key_env": "ANTHROPIC_API_KEY",
        "model": "claude-opus-5",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_env": "OLLAMA_API_KEY",
        "model": "qwen2.5-coder",
    },
}

DEFAULT_PROVIDER = "openrouter"
DEFAULT_MAX_TOKENS = 8192
MAX_STEPS = 20
MAX_VERIFY_NUDGES = 2
VERBOSE_PREVIEW_CHARS = 500

VERIFY_NUDGE = (
    "You wrote to a file and have not run anything since, so the fix is unverified. "
    "Re-run the reproduction case with run_python_file and report the output you "
    "actually saw. If there is genuinely nothing to run, say so and explain why."
)


def preview(result: str, limit: int = VERBOSE_PREVIEW_CHARS) -> str:
    """Shorten a tool result for the terminal. The model still receives all of it."""
    if len(result) <= limit:
        return result
    return f"{result[:limit]}... [{len(result) - limit} more characters]"


def update_verification(pending: bool, function_name: str, result: str) -> bool:
    """A write arms the verification gate; a run that actually executed clears it."""
    if result.startswith("Error:"):
        return pending
    if function_name == "write_file":
        return True
    if function_name == "run_python_file":
        return False
    return pending


def resolve_config(args: argparse.Namespace) -> dict:
    """Flag beats env var beats provider preset."""
    provider = args.provider or os.environ.get("HONE_PROVIDER") or DEFAULT_PROVIDER
    if provider not in PROVIDERS:
        known = ", ".join(sorted(PROVIDERS))
        raise SystemExit(f"Unknown provider {provider!r}. Known providers: {known}")

    preset = PROVIDERS[provider]
    key_env = preset["api_key_env"]
    api_key = os.environ.get("HONE_API_KEY") or os.environ.get(key_env)
    if not api_key:
        raise SystemExit(
            f"No API key for provider {provider!r}. "
            f"Set {key_env} (or HONE_API_KEY) in your .env."
        )

    return {
        "provider": provider,
        "base_url": args.base_url or os.environ.get("HONE_BASE_URL") or preset["base_url"],
        "model": args.model or os.environ.get("HONE_MODEL") or preset["model"],
        "max_tokens": int(os.environ.get("HONE_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
        "api_key": api_key,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="A coding agent for a sandboxed directory")
    parser.add_argument("user_prompt", type=str, help="User prompt")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        help=f"Endpoint preset (default: {DEFAULT_PROVIDER}, or $HONE_PROVIDER)",
    )
    parser.add_argument("--model", help="Model id, overriding the provider's default")
    parser.add_argument("--base-url", help="Endpoint URL, overriding the provider's default")
    args = parser.parse_args()

    load_dotenv()
    config = resolve_config(args)

    client = OpenAI(base_url=config["base_url"], api_key=config["api_key"])

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": args.user_prompt},
    ]

    if args.verbose:
        print(f"Provider: {config['provider']} ({config['base_url']})")
        print(f"Model: {config['model']}")

    verify_pending = False
    nudges = 0

    for _ in range(MAX_STEPS):

        response = client.chat.completions.create(
            model=config["model"],
            messages=messages,
            max_tokens=config["max_tokens"],
            tools=available_functions,
        )

        if not response.usage:
            raise RuntimeError(f"Failed API request to {config['base_url']}")

        if args.verbose:
            print(f"User prompt: {args.user_prompt}")
            print(f"Prompt tokens: {response.usage.prompt_tokens}")
            print(f"Response tokens: {response.usage.completion_tokens}")

        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            # Make sure that the agent re-runs the reproduction case after writing or editting with new updates
            if verify_pending and nudges < MAX_VERIFY_NUDGES:
                nudges += 1
                if args.verbose:
                    print(" - Unverified fix: asking the model to re-run the case")
                messages.append({"role": "user", "content": VERIFY_NUDGE})
                continue
            if verify_pending:
                print("Warning: the model wrote a file and answered without re-running the case.")
            print("Response:")
            print(message.content)
            break

        for tool_call in message.tool_calls:
            if tool_call.type != "function":
                continue
            result_message = call_function(tool_call, args.verbose)
            if not result_message["content"]:
                raise Exception("Tool message should have a non-empty 'content'")
            if args.verbose:
                print(f"-> {preview(result_message['content'])}")
            messages.append(result_message)
            verify_pending = update_verification(
                verify_pending, tool_call.function.name, result_message["content"]
            )

    else:
        print(f"Model requesting too many calls over the limit of {MAX_STEPS}")
        exit(1)

    return


if __name__ == "__main__":
    main()
