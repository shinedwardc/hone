import os


class SandboxEscape(Exception):
    """Raised when a path resolves to somewhere outside the sandbox root."""


def resolve_in_sandbox(working_directory: str, path: str) -> str:
    """Resolve `path` against the sandbox root and return its absolute location."""
    root = os.path.realpath(working_directory)
    target = os.path.realpath(os.path.join(root, path))

    try:
        contained = os.path.commonpath([root, target]) == root
    except ValueError:
        # Different drives (Windows) or a relative/absolute mix: not contained.
        contained = False

    if not contained:
        raise SandboxEscape(path)

    return target
