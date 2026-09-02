# hone

**A coding agent that reads, runs, and rewrites code inside a directory it cannot escape.**


## Run Example
```console
$ HONE_SANDBOX_ROOT=./examples/inventory uv run hone --provider anthropic \
    'main.py "widget:10" totals 27.0 even though tests.py passes; the 10-unit bulk discount should have applied.'
 - Calling function: get_files_info
 - Calling function: get_file_content
 - Calling function: get_file_content
 - Calling function: get_file_content
 - Calling function: get_files_info
 - Calling function: get_file_content
 - Calling function: run_python_file
 - Calling function: write_file
 - Calling function: run_python_file
 - Calling function: run_python_file
Response:
**Root cause:** `discount_rate` used a strict `>` comparison against each tier's minimum quantity, so a quantity exactly equal to a tier boundary (e.g. 10) fell through with no discount; the tests only check quantities strictly above the boundaries (25, 60), so they never exercised the boundary case, and `expected_total.py` confirms 10 units at the 10% rate should total 24.30.

**Fix:** Changed the comparison in `discount_rate` (pkg/pricing.py) from `quantity > minimum` to `quantity >= minimum`. Re-running `main.py "widget:10"` now gives total 24.3, matching the expected 24.3 from `expected_total.py`, and `tests.py` still passes (8/8).
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

Add `--verbose` to see the resolved configuration, token counts, the arguments of every tool call, and each tool's return value (previewed at 500 characters — the model still receives all of it):

```console
$ uv run hone --verbose "what does pkg/render.py do?"
Provider: openrouter (https://openrouter.ai/api/v1)
Model: openrouter/free
Sandbox: ./examples/calculator
User prompt: what does pkg/render.py do?
Prompt tokens: 892
Response tokens: 31
 - Calling function: get_file_content({'file_path': 'pkg/render.py', 'working_directory': './examples/calculator'})
-> def render(expression, result):
       ...
```

Without `--verbose`, each step prints only the name of the tool being called.

## Configuration

The endpoint is a **provider preset** — a base URL, a model, and the name of the key it reads. Pick one with `--provider`:

```bash
uv run hone --provider anthropic "what does pkg/render.py do?"
uv run hone --provider anthropic --model claude-sonnet-5 "..."
```

| Provider | Base URL | Default model | Key |
|---|---|---|---|
| `openrouter` (default) | `https://openrouter.ai/api/v1` | `openrouter/free` | `OPENROUTER_API_KEY` |
| `anthropic` | `https://api.anthropic.com/v1/` | `claude-sonnet-5` | `ANTHROPIC_API_KEY` |
| `ollama` | `http://localhost:11434/v1` | `qwen2.5-coder` | `OLLAMA_API_KEY` (unused locally) |

Every field resolves as **flag → environment variable → preset default**, so anything not listed above is still reachable without a code change:

| Variable | Flag | Default | Notes |
|---|---|---|---|
| `HONE_PROVIDER` | `--provider` | `openrouter` | Selects a row from the table above. |
| `HONE_MODEL` | `--model` | the preset's model | Any model id the endpoint accepts. |
| `HONE_BASE_URL` | `--base-url` | the preset's URL | Escape hatch for any OpenAI-compatible endpoint. |
| `HONE_API_KEY` | — | the preset's key variable | Overrides whichever key variable the provider names. |
| `HONE_MAX_TOKENS` | — | `8192` | Per-response output cap. |
| `HONE_SANDBOX_ROOT` | — | `./examples/calculator` | The directory the agent cannot escape. Point it at another workspace, e.g. `./examples/inventory`. |

Only the selected provider's key has to be set. If neither `HONE_API_KEY` nor the preset's key variable is present, the run exits before making a request and names the variable it looked for.

## The tool surface

Four tools touch the filesystem, and all of their paths are relative to the sandbox root. `ask_user` talks to the person instead, so it is the one tool that gets no `working_directory`.

| Tool | Arguments | Behavior |
|---|---|---|
| `get_files_info` | `directory` (optional, defaults to root) | Lists the entries directly inside the directory with byte size and directory flag. Not recursive — call again with a subdirectory. |
| `get_file_content` | `file_path` | Returns contents, truncated at 10,000 characters with a marker at the cut. |
| `write_file` | `file_path`, `content` | Overwrites the **entire** file, creating parent directories as needed. There is no partial-edit or patch tool, so the model has to resend the whole file. |
| `run_python_file` | `file_path`, `args` (optional, list of strings) | Executes with the sandbox root as CWD; returns STDOUT, STDERR, and the exit code when it is nonzero. 30s timeout, `.py` files only. |
| `ask_user` | `question` | Prints the question and waits for one typed answer. Offered on the first turn only, since a task that never said what to fix is visible before any investigation. Used to strengthen and guide model decisions. |

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
  │ hone/tools/*.py — call hone/sandbox.py to    │
  │ resolve the path inside the root, touch disk │
  └──────────────────────────────────────────────┘
```

## License

MIT — see [LICENSE](LICENSE).
