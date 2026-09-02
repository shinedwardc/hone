"""A question is the first thing a run does, or it is not asked at all."""

import builtins
from types import SimpleNamespace

import pytest

from hone.dispatch import SANDBOX_FREE, tools_for
from hone.tools.ask_user import ask_user


@pytest.fixture
def at_a_terminal(monkeypatch):
    """Pretend someone is watching, and script what they type."""

    def _typed(reply):
        # Makes ask_user believe a human is watching
        monkeypatch.setattr("sys.stdin", SimpleNamespace(isatty=lambda: True))
        # Makes built-in input() return a canned string instead of blocking for typing
        monkeypatch.setattr(builtins, "input", lambda *_: reply)

    return _typed


def test_the_tool_is_offered_only_while_the_run_may_ask():
    """Assert ask_user appears only in the toolset that still permits asking"""
    offered = [schema["function"]["name"] for schema in tools_for(True)]
    withheld = [schema["function"]["name"] for schema in tools_for(False)]

    assert "ask_user" in offered
    assert "ask_user" not in withheld
    # Withholding the question must not disturb the tools that were already there.
    assert offered[: len(withheld)] == withheld


def test_ask_user_takes_no_working_directory():
    """Assert ask_user is dispatched without a sandbox root"""
    assert "ask_user" in SANDBOX_FREE


def test_an_unanswerable_run_tells_the_model_to_assume(monkeypatch):
    """Assert a non-interactive stdin returns an error telling the model to assume"""
    monkeypatch.setattr("sys.stdin", SimpleNamespace(isatty=lambda: False))

    result = ask_user("What should the total be?")

    assert result.startswith("Error:")
    assert "not interactive" in result
    assert "state that assumption" in result


def test_an_empty_question_is_rejected_without_bothering_anyone(at_a_terminal):
    """Assert a blank question is rejected before anyone is prompted"""
    at_a_terminal("24.30")

    assert ask_user("   ") == "Error: ask_user needs a non-empty question."


def test_the_answer_comes_back_to_the_model(at_a_terminal, capsys):
    """Assert the typed answer is stripped and returned, and the question is printed"""
    at_a_terminal("  it should be 24.30  ")

    result = ask_user("What should the total be?")

    assert result == "The user answered: it should be 24.30"
    assert "What should the total be?" in capsys.readouterr().out


def test_a_skipped_question_falls_back_to_assuming(at_a_terminal):
    """Assert an empty reply counts as skipped and tells the model to assume"""
    at_a_terminal("")

    result = ask_user("What should the total be?")

    assert result.startswith("Error:")
    assert "skipped" in result
    assert "state that assumption" in result


@pytest.mark.parametrize("interruption", [EOFError, KeyboardInterrupt])
def test_walking_away_does_not_crash_the_run(monkeypatch, interruption):
    """Assert EOF or Ctrl-C returns an error instead of propagating"""
    def _interrupt(*_):
        raise interruption

    monkeypatch.setattr("sys.stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(builtins, "input", _interrupt)

    result = ask_user("What should the total be?")

    assert result.startswith("Error:")
    assert "state that assumption" in result
