from hone.tools.read_file import MAX_CHARS, get_file_content


def test_returns_the_whole_file(sandbox, write):
    """Assert a file's full contents come back unchanged"""
    write("main.py", "print('hello')\n")

    assert get_file_content(sandbox, "main.py") == "print('hello')\n"


def test_reads_a_nested_file(sandbox, write):
    """Assert a file in a subdirectory is read by its relative path"""
    write("pkg/calculator.py", "class Calculator:\n    pass\n")

    assert "class Calculator" in get_file_content(sandbox, "pkg/calculator.py")


def test_empty_file_returns_empty_string(sandbox, write):
    """Assert an empty file returns an empty string, not an error"""
    write("empty.txt", "")

    assert get_file_content(sandbox, "empty.txt") == ""


def test_long_file_is_truncated_with_a_marker(sandbox, write):
    """Assert content past MAX_CHARS is cut and a truncation marker appended"""
    write("lorem.txt", "a" * (MAX_CHARS + 500))

    result = get_file_content(sandbox, "lorem.txt")

    assert result.startswith("a" * MAX_CHARS)
    assert result.endswith(f'[...File "lorem.txt" truncated at {MAX_CHARS} characters]')


def test_file_at_exactly_the_limit_is_not_truncated(sandbox, write):
    """Assert a file of exactly MAX_CHARS is returned whole"""
    write("exact.txt", "a" * MAX_CHARS)

    result = get_file_content(sandbox, "exact.txt")

    assert result == "a" * MAX_CHARS
    assert "truncated" not in result


def test_file_one_char_over_the_limit_is_truncated(sandbox, write):
    """Assert one character past the limit triggers truncation"""
    write("over.txt", "a" * (MAX_CHARS + 1))

    assert "truncated" in get_file_content(sandbox, "over.txt")


def test_file_outside_the_sandbox_is_refused(sandbox):
    """Assert an absolute path outside the sandbox is refused"""
    result = get_file_content(sandbox, "/bin/cat")

    assert result == 'Error: Cannot read "/bin/cat" as it is outside the permitted working directory'


def test_parent_traversal_is_refused(sandbox):
    """Assert a path climbing above the sandbox root is refused"""
    result = get_file_content(sandbox, "../secret.txt")

    assert result == 'Error: Cannot read "../secret.txt" as it is outside the permitted working directory'


def test_missing_file_is_reported(sandbox):
    """Assert a nonexistent path returns the not-a-regular-file error"""
    result = get_file_content(sandbox, "pkg/does_not_exist.py")

    assert result == 'Error: File not found or is not a regular file: "pkg/does_not_exist.py"'


def test_directory_is_not_a_regular_file(sandbox, write):
    """Assert a directory is rejected rather than read"""
    write("pkg/calculator.py", "x")

    assert get_file_content(sandbox, "pkg") == 'Error: File not found or is not a regular file: "pkg"'
