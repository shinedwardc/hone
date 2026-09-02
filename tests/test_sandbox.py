import os

import pytest

from hone.sandbox import SandboxEscape, resolve_in_sandbox


def test_resolves_relative_path_inside_root(sandbox):
    """Assert a relative path resolves to an absolute path under the root"""
    resolved = resolve_in_sandbox(sandbox, "pkg/calculator.py")

    assert resolved == os.path.join(os.path.realpath(sandbox), "pkg", "calculator.py")
    assert os.path.isabs(resolved)


def test_resolves_dot_to_the_root_itself(sandbox):
    """Assert a lone dot resolves to the real root path"""
    assert resolve_in_sandbox(sandbox, ".") == os.path.realpath(sandbox)


def test_interior_traversal_that_stays_inside_is_allowed(sandbox):
    """Assert a double dot is allowed while the result stays inside the root"""
    resolved = resolve_in_sandbox(sandbox, "pkg/../main.py")

    assert resolved == os.path.join(os.path.realpath(sandbox), "main.py")


@pytest.mark.parametrize(
    "escaping_path",
    [
        "../",
        "../../etc/passwd",
        "pkg/../../outside.py",
        "/bin/cat",
        "/etc/passwd",
    ],
)
def test_paths_outside_the_root_are_rejected(sandbox, escaping_path):
    """Assert every path landing outside the root raises SandboxEscape"""
    with pytest.raises(SandboxEscape):
        resolve_in_sandbox(sandbox, escaping_path)


def test_sibling_directory_sharing_a_name_prefix_is_rejected(tmp_path):
    """`/x/root` must not be treated as containing `/x/root_evil`."""
    root = tmp_path / "root"
    root.mkdir()
    (tmp_path / "root_evil").mkdir()

    with pytest.raises(SandboxEscape):
        resolve_in_sandbox(str(root), "../root_evil")


def test_symlink_pointing_outside_the_root_is_rejected(tmp_path):
    """Assert a symlink is followed and refused when its target sits outside"""
    root = tmp_path / "root"
    root.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("classified")
    os.symlink(secret, root / "link.txt")

    with pytest.raises(SandboxEscape):
        resolve_in_sandbox(str(root), "link.txt")


def test_escape_carries_the_offending_path(sandbox):
    """Assert the raised error names the path that was refused"""
    with pytest.raises(SandboxEscape) as excinfo:
        resolve_in_sandbox(sandbox, "../nope")

    assert "../nope" in str(excinfo.value)
