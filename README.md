# hone

**A coding agent that reads, runs, and rewrites code inside a directory it cannot escape.**

hone hands a language model four tools — list, read, write, execute — and runs them in a loop until the job is done. Every path the model supplies is resolved and checked against a working-directory root before it touches disk, and the model never gets to pick that root.

```console
$ uv run hone "the calculator gets operator precedence wrong"
 - Calling function: get_files_info
 - Calling function: get_file_content
 - Calling function: run_python_file
 - Calling function: write_file
 - Calling function: run_python_file
Response:
Root cause: the evaluator applied operators left-to-right in the order they
appeared, ignoring precedence, so `3 * 4 + 5` was parsed as `3 * (4 + 5)`.

I added a precedence map and sorted operator application by it. Re-ran
`main.py "3 * 4 + 5"`: it now returns 17 (was 27).
```

## Why

Language models are good at proposing fixes and bad at confirming them. Tool using AI agents narrow the gap, but they have a tendency to run a general test rather than the failing case itself, calling a fix verified on the strength of the edit rather than a re-run with the fixes. A bug report is usually a case the suite doesn't cover. They are prone to report fixes, without ever running and verifying the case you actually reported.

In hone, the agent looks at the codebase before it theorizes and re-run before it claims. It's system prompt encodes an explicit protocol: reproduce the failure, read the source, state the root cause in one specific sentence, make the smallest change that addresses it, then re-run the same case and verify.

The other half of the point is that you pick the provider, and it runs on your machine. Every hosted coding agent decides for you which model reads your code and where that code goes.

hone runs in your terminal, on your checkout, as a normal process. The files it reads are the files on your disk, the code it executes runs in your shell's environment, and the only thing that leaves the machine is the conversation you send to the model you chose, nothing at all if your model is local.

## What it does

- **Clear working directory guidelines.** `working_directory` is injected by the dispatcher after the model's arguments are parsed, so it can't be overridden by anything the model emits. Tools receive relative paths only.
- **Every path is verified.** Each tool resolves the target against the sandbox root and refuses anything that lands outside it, returning an error string instead of raising.
- **Errors go back to the model.** Malformed JSON arguments, unknown function names, and bad signatures all become tool-result messages telling the model what went wrong so it can retry.
- **A debugging protocol, not just a system prompt.** Reproduce → read → root-cause → minimal-fix → re-verify.
- **Bring your own model, locally or hosted.** Built on the OpenAI SDK, any OpenAI-compatible endpoint works. `--provider` picks a preset (OpenRouter, Anthropic, or a local Ollama server), you can also set `--model` and `--base-url` to override it.

## Getting started

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- An API key for one provider: [OpenRouter](https://openrouter.ai/) or a model of your choice.

### Install

```bash
git clone https://github.com/shinedwardc/hone.git
cd hone
uv sync
cp .env.example .env    # then add your key
```

### Run

```bash
uv run hone "list the files in this project and tell me what it does"
```

Add `--verbose` to see token counts, the arguments of every tool call, and each tool's return value:

```console
$ uv run hone --verbose "what does pkg/render.py do?"
User prompt: what does pkg/render.py do?
Prompt tokens: 892
Response tokens: 31
 - Calling function: get_file_content({'file_path': 'pkg/render.py', 'working_directory': './examples/calculator'})
-> def render(expression, result):
       ...
```

## Configuration

The endpoint is a **provider preset** — a base URL, a model, and the name of the key it reads. Pick one with `--provider`:

```bash
uv run hone --provider anthropic "what does pkg/render.py do?"
uv run hone --provider anthropic --model claude-sonnet-5 "..."
```

| Provider | Base URL | Default model | Key |
|---|---|---|---|
| `openrouter` (default) | `https://openrouter.ai/api/v1` | `openrouter/free` | `OPENROUTER_API_KEY` |
| `anthropic` | `https://api.anthropic.com/v1/` | `claude-opus-5` | `ANTHROPIC_API_KEY` |
| `ollama` | `http://localhost:11434/v1` | `qwen2.5-coder` | `OLLAMA_API_KEY` (unused locally) |

Every field resolves as **flag → environment variable → preset default**, so anything not listed above is still reachable without a code change:

| Variable | Flag | Default | Notes |
|---|---|---|---|
| `HONE_PROVIDER` | `--provider` | `openrouter` | Selects a row from the table above. |
| `HONE_MODEL` | `--model` | the preset's model | Any model id the endpoint accepts. |
| `HONE_BASE_URL` | `--base-url` | the preset's URL | Escape hatch for any OpenAI-compatible endpoint. |
| `HONE_API_KEY` | — | the preset's key variable | Overrides whichever key variable the provider names. |
| `HONE_MAX_TOKENS` | — | `8192` | Per-response output cap. |
| `HONE_SANDBOX_ROOT` | — | `./examples/calculator` | The directory the agent cannot escape. |

Anthropic is reached through its OpenAI-compatible endpoint, which covers chat and tool calling but not extended thinking or prompt caching. Using those would mean adding the native `anthropic` SDK alongside the OpenAI one.

## The tool surface

All paths are relative to the sandbox root.

| Tool | Arguments | Behavior |
|---|---|---|
| `get_files_info` | `directory` (optional, defaults to root) | Lists entries with byte size and directory flag. |
| `get_file_content` | `file_path` | Returns contents, truncated at 10,000 characters with a marker. |
| `write_file` | `file_path`, `content` | Writes or overwrites, creating parent directories as needed. |
| `run_python_file` | `file_path`, `args` (optional) | Executes with the sandbox root as CWD; returns stdout, stderr, and exit code. 30s timeout. |

## How it works

```
  your prompt
       │
       ▼
  ┌──────────────────────────────────────────────┐
  │ hone/cli.py — the agent loop (max 20 passes) │
  └──────────────────────────────────────────────┘
       │  messages[]                    ▲
       ▼                                │ tool results
  provider    ──►  tool_calls? ──no──►  print, exit
   (openai SDK)         │
                       yes
                        ▼
  ┌──────────────────────────────────────────────┐
  │ hone/dispatch.py — tool dispatch             │
  │  · parse JSON args (errors → tool message)   │
  │  · inject working_directory (not model-set)  │
  │  · route name → callable                     │
  └──────────────────────────────────────────────┘
                        │
                        ▼
  ┌──────────────────────────────────────────────┐
  │ hone/tools/*.py — resolve path, check it is  │
  │ inside the root, then touch disk             │
  └──────────────────────────────────────────────┘
```

The agent is a single package, `hone/`, plus the sample workspace it ships with:

- **`hone/cli.py`** — argument and provider-preset resolution, client setup, the bounded loop, and the terminal condition (a model response with no tool calls).
- **`hone/dispatch.py`** — turns a tool call into a tool result, converting every failure mode into a message the model can act on.
- **`hone/tools/`** — the four tools. Each one owns its own schema and its own path check.
- **`hone/prompts.py`** — the system prompt and the debugging protocol.
- **`examples/calculator/`** — a small sample app used as the default workspace to exercise the agent against.

## License

MIT — see [LICENSE](LICENSE).
