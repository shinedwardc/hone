import os

from hone.tools.list_dir import get_files_info


def test_lists_files_with_size_and_directory_flag(sandbox, write):
    """Assert get_files_info return the correct output format"""
    write("main.py", "print('hi')")
    os.makedirs(os.path.join(sandbox, "pkg"))

    result = get_files_info(sandbox, ".")

    assert " - main.py: file_size=11 bytes, is_dir=False" in result
    assert " - pkg: file_size=" in result
    assert "is_dir=True" in result


def test_current_directory_is_labelled_current(sandbox, write):
    """Assert "." is labelled as the current directory in the header"""
    write("main.py", "x")

    assert get_files_info(sandbox, ".").startswith("Result for current directory:")


def test_named_directory_is_labelled_with_its_path(sandbox, write):
    """Assert a named subdirectory is labelled with its own path in the header"""
    write("pkg/calculator.py", "x")

    assert get_files_info(sandbox, "pkg").startswith('Result for "pkg" directory:')


def test_defaults_to_the_working_directory(sandbox, write):
    """Assert omitting the directory argument behaves the same as passing '.'"""
    write("main.py", "x")

    assert get_files_info(sandbox) == get_files_info(sandbox, ".")


def test_lists_every_entry_in_the_directory(sandbox, write):
    """Assert every direct child is listed, files and directories, with no extras"""
    write("a.py", "")
    write("b.txt", "")
    write("pkg/c.py", "")

    lines = get_files_info(sandbox, ".").splitlines()[1:]
    names = {line.split(":")[0].removeprefix(" - ") for line in lines}

    assert names == {"a.py", "b.txt", "pkg"}


def test_empty_directory_returns_only_the_header(sandbox):
    """Assert an empty directory returns the header and no entry lines"""
    assert get_files_info(sandbox, ".") == "Result for current directory:\n"


def test_directory_outside_the_sandbox_is_refused(sandbox):
    """Assert an absolute path outside the sandbox is refused with an error"""
    result = get_files_info(sandbox, "/bin")

    assert result == 'Error: Cannot list "/bin" as it is outside the permitted working directory'


def test_parent_directory_is_refused(sandbox):
    """Assert a relative path escaping above the sandbox root is refused with an error"""
    result = get_files_info(sandbox, "../")

    assert result == 'Error: Cannot list "../" as it is outside the permitted working directory'


def test_file_argument_is_rejected_as_not_a_directory(sandbox, write):
    """Assert an existing file passed as the directory is rejected"""
    write("main.py", "x")

    assert get_files_info(sandbox, "main.py") == 'Error: "main.py" is not a directory'


def test_missing_directory_is_rejected_as_not_a_directory(sandbox):
    """Assert a path that does not exist is rejected as not a directory"""
    assert get_files_info(sandbox, "nope") == 'Error: "nope" is not a directory'
