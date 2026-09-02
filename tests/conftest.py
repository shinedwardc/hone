import os

import pytest


@pytest.fixture
def sandbox(tmp_path):
    """Temporary directory as an isolated working directory for the agent's sandbox root."""
    return str(tmp_path)


@pytest.fixture
def write(sandbox):
    """Create a file inside the sandbox and return its absolute path."""

    def _write(relative_path: str, content: str = "") -> str:
        path = os.path.join(sandbox, relative_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        return path

    return _write
