# hone

**A coding agent that reads, runs, and rewrites code inside a directory it cannot escape.**

hone hands a language model four tools — list, read, write, execute — and runs them in a loop until the job is done. Every path the model supplies is resolved and checked against a working-directory root before it touches disk, and the model never gets to pick that root.

```console
$ uv run main.py "the calculator gets operator precedence wrong"
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

Language models are good at proposing fixes and bad at confirming them. Ask one to fix a bug and it will happily describe a change it never ran, to a file it never opened, and call the result "fixed."

hone is built around the opposite default: the agent has to *look* before it theorizes and *re-run* before it claims. Its system prompt encodes an explicit protocol — reproduce the failure, read the source, state the root cause in one specific sentence, make the smallest change that addresses it, then re-run the same case and verify. It isn't allowed to report a bug fixed unless it re-ran the code in the same turn. Giving a model real filesystem and execution access is only reasonable if you also bound where it can reach and hold it to evidence, so those two things are the design.

## What it does

- **The working directory is not the model's to choose.** `working_directory` is injected by the dispatcher after the model's arguments are parsed, so it can't be overridden by anything the model emits. Tools receive relative paths only.
- **Every path is checked before it's used.** Each tool resolves the target against the sandbox root and refuses anything that lands outside it, returning an error string instead of raising.
- **Errors go back to the model, not up the stack.** Malformed JSON arguments, unknown function names, and bad signatures all become tool-result messages telling the model what went wrong so it can retry — a stack trace would end the run.
- **A debugging protocol, not just a system prompt.** The reproduce → read → root-cause → minimal-fix → re-verify loop is spelled out in `prompts.py`, including what to do after three failed attempts.
- **Every loop is bounded.** 20 tool-calling iterations per run, a 30-second timeout on subprocess execution, and a 10,000-character cap on file reads.
- **Provider-portable.** Built on the OpenAI SDK against an OpenRouter base URL, so switching models is a one-line change and switching providers is a two-line one.

## Getting started

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- An [OpenRouter](https://openrouter.ai/) API key

### Install

```bash
git clone https://github.com/shinedwardc/hone.git
cd hone
uv sync
cp .env.example .env    # then add your key
```

### Run

```bash
uv run main.py "list the files in this project and tell me what it does"
```

Add `--verbose` to see token counts, the arguments of every tool call, and each tool's return value:

```console
$ uv run main.py --verbose "what does pkg/render.py do?"
User prompt: what does pkg/render.py do?
Prompt tokens: 892
Response tokens: 31
 - Calling function: get_file_content({'file_path': 'pkg/render.py', 'working_directory': './calculator'})
-> def render(expression, result):
       ...
```

## Configuration

| Variable | Required | Default | Notes |
|---|---|---|---|
| `OPENROUTER_API_KEY` | Yes | — | Read from `.env` via `python-dotenv`. The program exits with a `RuntimeError` if it isn't set. |

The model (`openrouter/free`) and the sandbox root (`./calculator`) are currently constants in `main.py` and `call_function.py`. Making both configurable is on the roadmap.

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
  ┌─────────────────────────────────────────────┐
  │ main.py — the agent loop (max 20 passes)    │
  └─────────────────────────────────────────────┘
       │  messages[]                    ▲
       ▼                                │ tool results
  OpenRouter  ──►  tool_calls? ──no──►  print, exit
   (openai SDK)         │
                       yes
                        ▼
  ┌─────────────────────────────────────────────┐
  │ call_function.py — dispatch                 │
  │  · parse JSON args (errors → tool message)  │
  │  · inject working_directory (not model-set) │
  │  · route name → callable                    │
  └─────────────────────────────────────────────┘
                        │
                        ▼
  ┌─────────────────────────────────────────────┐
  │ functions/*.py — resolve path, check it is  │
  │ inside the root, then touch disk            │
  └─────────────────────────────────────────────┘
```

- **`main.py`** — CLI parsing, client setup, the bounded loop, and the terminal condition (a model response with no tool calls).
- **`call_function.py`** — turns a tool call into a tool result, converting every failure mode into a message the model can act on.
- **`functions/`** — the four tools. Each one owns its own schema and its own path check.
- **`prompts.py`** — the system prompt and the debugging protocol.
- **`calculator/`** — a small sample app used as the default workspace to exercise the agent against.

## Roadmap

- **Harden the sandbox against symlinks.** Path checks currently resolve with `abspath`, which doesn't follow links — a symlink inside the root pointing outside it would escape. Moving to `realpath` closes this, and it deserves a test suite that tries to break in.
- **A real test suite.** pytest with fixtures that never mutate the sample app, covering dispatch, the iteration cap, and the schemas themselves.
- **Configurable working directory and model.** `--working-dir` and `--model` flags, so the agent isn't tied to the bundled sample app.
- **Install as `hone`.** A console entry point, so it's `hone "..."` rather than `uv run main.py "..."`.
- **Multi-turn sessions.** Today each invocation is one prompt and one process; keeping the conversation alive makes iterating on a fix far cheaper.

## License

<!-- TODO: add a LICENSE file and name it here. MIT is the usual choice for a portfolio project. -->
