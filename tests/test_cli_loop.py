import json
from types import SimpleNamespace

import pytest

from hone import cli
from hone.cli import preview, update_verification


def tool_call(name: str, **arguments):
    return SimpleNamespace(
        id=f"call_{name}",
        type="function",
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


def answer(content: str):
    return SimpleNamespace(content=content, tool_calls=None)


def calls(*tool_calls):
    return SimpleNamespace(content=None, tool_calls=list(tool_calls))


class FakeCompletions:
    """Replays scripted assistant messages and records what it was sent."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if not self.script:
            raise AssertionError("the loop asked for more responses than were scripted")
        return SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
            choices=[SimpleNamespace(message=self.script.pop(0))],
        )


@pytest.fixture
def run_agent(monkeypatch, sandbox):
    """Run the real loop against scripted model responses and a throwaway sandbox."""

    def _run(script, prompt="fix the bug", argv_extra=()):
        fake = FakeCompletions(script)
        client = SimpleNamespace(chat=SimpleNamespace(completions=fake))

        monkeypatch.setattr(cli, "load_dotenv", lambda: None)
        monkeypatch.setattr(cli, "OpenAI", lambda **kwargs: client)
        monkeypatch.setenv("HONE_SANDBOX_ROOT", str(sandbox))
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.setattr("sys.argv", ["hone", prompt, *argv_extra])

        cli.main()
        return fake

    return _run


def sent_contents(request):
    """The plain-text content of every message in one API request."""
    return [
        message["content"]
        for message in request["messages"]
        if isinstance(message, dict) and isinstance(message.get("content"), str)
    ]


def test_answer_without_any_write_is_accepted(run_agent, capsys):
    """Assert an answer with no write behind it goes through in one request"""
    fake = run_agent([answer("main.py renders the expression.")])

    assert len(fake.requests) == 1
    assert "main.py renders the expression." in capsys.readouterr().out


def test_answer_after_a_write_is_pushed_back_until_the_case_is_rerun(run_agent, capsys):
    """Assert answering after a write earns a nudge until the case is re-run"""
    fake = run_agent(
        [
            calls(tool_call("write_file", file_path="main.py", content="print(17)")),
            answer("Fixed it."),
            calls(tool_call("run_python_file", file_path="main.py")),
            answer("Verified: it prints 17."),
        ]
    )

    assert len(fake.requests) == 4
    assert cli.VERIFY_NUDGE in sent_contents(fake.requests[2])

    out = capsys.readouterr().out
    assert "Verified: it prints 17." in out
    assert "Warning:" not in out


def test_a_rerun_before_answering_passes_straight_through(run_agent, capsys):
    """Assert a write followed by a re-run needs no nudge"""
    fake = run_agent(
        [
            calls(tool_call("write_file", file_path="main.py", content="print(17)")),
            calls(tool_call("run_python_file", file_path="main.py")),
            answer("Verified: it prints 17."),
        ]
    )

    assert len(fake.requests) == 3
    assert not any(cli.VERIFY_NUDGE in sent_contents(r) for r in fake.requests)
    assert "Warning:" not in capsys.readouterr().out


def test_write_and_rerun_in_one_turn_clears_the_gate(run_agent, capsys):
    """Assert a write and a re-run in the same turn clear the gate"""
    fake = run_agent(
        [
            calls(
                tool_call("write_file", file_path="main.py", content="print(17)"),
                tool_call("run_python_file", file_path="main.py"),
            ),
            answer("Verified: it prints 17."),
        ]
    )

    assert len(fake.requests) == 2
    assert "Warning:" not in capsys.readouterr().out


def test_a_failed_write_does_not_arm_the_gate(run_agent, capsys):
    """Assert a rejected write leaves the gate disarmed"""
    fake = run_agent(
        [
            calls(tool_call("write_file", file_path="../escape.py", content="x")),
            answer("I could not write outside the sandbox."),
        ]
    )

    assert len(fake.requests) == 2
    assert "Warning:" not in capsys.readouterr().out


def test_a_failed_rerun_leaves_the_gate_armed(run_agent, capsys):
    """Assert a re-run that errors does not count as verification"""
    fake = run_agent(
        [
            calls(tool_call("write_file", file_path="main.py", content="print(17)")),
            calls(tool_call("run_python_file", file_path="missing.py")),
            answer("Fixed it."),
            calls(tool_call("run_python_file", file_path="main.py")),
            answer("Verified: it prints 17."),
        ]
    )

    assert len(fake.requests) == 5
    assert cli.VERIFY_NUDGE in sent_contents(fake.requests[3])


def test_the_gate_gives_up_after_its_reminders_and_warns(run_agent, capsys):
    """Assert the gate stops nudging after MAX_VERIFY_NUDGES and warns instead"""
    script = [calls(tool_call("write_file", file_path="main.py", content="print(17)"))]
    script += [answer("Fixed it.")] * (cli.MAX_VERIFY_NUDGES + 1)

    fake = run_agent(script)

    assert len(fake.requests) == cli.MAX_VERIFY_NUDGES + 2

    out = capsys.readouterr().out
    assert "Warning: the model wrote a file and answered without re-running the case." in out
    assert "Fixed it." in out


def test_the_nudge_is_announced_in_verbose_mode(run_agent, capsys):
    """Assert verbose mode reports when the nudge is sent"""
    run_agent(
        [
            calls(tool_call("write_file", file_path="main.py", content="print(17)")),
            answer("Fixed it."),
            calls(tool_call("run_python_file", file_path="main.py")),
            answer("Verified: it prints 17."),
        ],
        argv_extra=("--verbose",),
    )

    assert "Unverified fix: asking the model to re-run the case" in capsys.readouterr().out


@pytest.mark.parametrize(
    "pending, name, result, expected",
    [
        (False, "write_file", 'Successfully wrote to "main.py" (9 characters written)', True),
        (True, "run_python_file", "STDOUT: 17\n", False),
        (True, "run_python_file", "Process exited with code 1\nSTDERR: boom", False),
        (True, "run_python_file", 'Error: "missing.py" does not exist or is not a regular file', True),
        (False, "write_file", 'Error: Cannot write to "../x" as it is outside the permitted working directory', False),
        (True, "get_file_content", "def render(): ...", True),
        (False, "get_files_info", "Result for current directory:", False),
    ],
)
def test_update_verification(pending, name, result, expected):
    """Assert the gate arms on successful writes and disarms only on successful re-runs"""
    assert update_verification(pending, name, result) is expected


def test_verbose_truncates_a_long_tool_result(run_agent, write, capsys):
    """Assert verbose mode shortens a long tool result and counts the remainder"""
    write("big.txt", "x" * 2000)

    run_agent(
        [
            calls(tool_call("get_file_content", file_path="big.txt")),
            answer("It is a wall of x."),
        ],
        argv_extra=("--verbose",),
    )

    out = capsys.readouterr().out
    assert "x" * 2000 not in out
    assert "... [1500 more characters]" in out


def test_verbose_prints_a_short_tool_result_in_full(run_agent, write, capsys):
    """Assert verbose mode prints a short tool result untruncated"""
    write("small.txt", "just a little")

    run_agent(
        [
            calls(tool_call("get_file_content", file_path="small.txt")),
            answer("Read it."),
        ],
        argv_extra=("--verbose",),
    )

    out = capsys.readouterr().out
    assert "-> just a little" in out
    assert "more characters]" not in out


def test_the_model_still_receives_the_untruncated_result(run_agent, write):
    """Assert truncation is display only; the model still gets the full result"""
    write("big.txt", "x" * 2000)

    fake = run_agent(
        [
            calls(tool_call("get_file_content", file_path="big.txt")),
            answer("It is a wall of x."),
        ],
        argv_extra=("--verbose",),
    )

    assert "x" * 2000 in sent_contents(fake.requests[1])


@pytest.mark.parametrize(
    "result, limit, expected",
    [
        ("short", 10, "short"),
        ("exactly-10", 10, "exactly-10"),
        ("eleven chars", 10, "eleven cha... [2 more characters]"),
        ("", 10, ""),
    ],
)
def test_preview(result, limit, expected):
    """Assert preview cuts only past the limit and appends the remaining count"""
    assert preview(result, limit) == expected


def last_tool_content(request):
    """The most recent tool result the loop put in front of the model."""
    return [
        message["content"]
        for message in request["messages"]
        if isinstance(message, dict) and message.get("role") == "tool"
    ][-1]


def offered(request):
    """The tool names the loop put in front of the model for one turn."""
    return [schema["function"]["name"] for schema in request["tools"]]


def test_the_question_is_offered_on_the_first_turn(run_agent):
    """Assert ask_user is in the toolset before the run has looked at anything"""
    fake = run_agent([answer("Nothing to fix.")], prompt="fix the problem")

    assert "ask_user" in offered(fake.requests[0])


def test_the_question_is_withdrawn_once_the_run_has_looked(run_agent):
    """Assert ask_user is dropped from the toolset after the first tool call"""
    fake = run_agent(
        [
            calls(tool_call("get_files_info", directory=".")),
            answer("Read the tree."),
        ]
    )

    assert "ask_user" in offered(fake.requests[0])
    assert "ask_user" not in offered(fake.requests[1])


def test_asking_is_withdrawn_by_the_question_itself(run_agent):
    """Assert asking once withdraws the tool and reports stdin is not interactive"""
    fake = run_agent(
        [
            calls(tool_call("ask_user", question="Which behaviour is wrong?")),
            answer("Assuming the precedence bug."),
        ],
        prompt="fix the problem",
    )

    assert "ask_user" in offered(fake.requests[0])
    assert "ask_user" not in offered(fake.requests[1])
    assert "not interactive" in last_tool_content(fake.requests[1])


def test_the_diagnosis_question_this_replaces_is_refused(run_agent, write):
    """The real failure: the model ran the case, diagnosed it, then quizzed the user."""
    write("main.py", "print(27.0)")

    fake = run_agent(
        [
            calls(tool_call("run_python_file", file_path="main.py")),
            calls(
                tool_call(
                    "ask_user",
                    question=(
                        "Precedence looks reversed. What should the values be for "
                        "+, -, *, / in standard mathematical order of operations?"
                    ),
                )
            ),
            answer("Precedence was inverted; corrected it."),
        ]
    )

    # Withdrawn from the toolset, and still refused if the model calls it anyway.
    assert "ask_user" not in offered(fake.requests[1])
    assert cli.ASK_TOO_LATE == last_tool_content(fake.requests[2])


def test_a_second_question_in_the_same_turn_is_refused(run_agent):
    """Assert only the first ask_user in a turn is honoured"""
    fake = run_agent(
        [
            calls(
                tool_call("ask_user", question="Which behaviour is wrong?"),
                tool_call("ask_user", question="Are you sure?"),
            ),
            answer("Assuming the precedence bug."),
        ],
        prompt="fix the problem",
    )

    assert cli.ASK_TOO_LATE == last_tool_content(fake.requests[1])


def test_a_question_does_not_disarm_the_verification_gate(run_agent, write, capsys):
    """Assert an early question leaves the write-then-verify gate intact"""
    write("main.py", "print(20)")

    fake = run_agent(
        [
            calls(tool_call("ask_user", question="Which behaviour is wrong?")),
            calls(tool_call("write_file", file_path="main.py", content="print(17)")),
            answer("Fixed it."),
            calls(tool_call("run_python_file", file_path="main.py")),
            answer("Verified: it prints 17."),
        ],
        prompt="fix the problem",
    )

    assert cli.VERIFY_NUDGE in sent_contents(fake.requests[3])
    assert "Warning:" not in capsys.readouterr().out
