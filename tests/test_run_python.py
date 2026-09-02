import os

from hone.tools.run_python import run_python_file

def test_captures_stdout(sandbox, write):
    """Assert the script's stdout comes back under a STDOUT label"""
    write("main.py", "print('hello from main')")

    result = run_python_file(sandbox, "main.py")

    assert result == "STDOUT: hello from main\n"


def test_passes_arguments_through(sandbox, write):
    """Assert extra arguments reach the script as sys.argv"""
    write("main.py", "import sys\nprint(' '.join(sys.argv[1:]))")

    result = run_python_file(sandbox, "main.py", ["3", "+", "5"])

    assert "STDOUT: 3 + 5\n" in result


def test_runs_with_the_sandbox_as_the_working_directory(sandbox, write):
    """Assert the script runs with the sandbox root as its cwd"""
    write("main.py", "import os\nprint(os.getcwd())")

    result = run_python_file(sandbox, "main.py")

    assert "STDOUT:" in result
    assert result.strip().endswith(os.path.realpath(sandbox))


def test_imports_resolve_relative_to_the_sandbox(sandbox, write):
    """Assert a package inside the sandbox is importable by the script"""
    write("pkg/__init__.py", "")
    write("pkg/calculator.py", "VALUE = 42")
    write("main.py", "from pkg.calculator import VALUE\nprint(VALUE)")

    assert "STDOUT: 42\n" in run_python_file(sandbox, "main.py")


def test_silent_script_reports_no_output(sandbox, write):
    """Assert a script that prints nothing reports no output"""
    write("quiet.py", "x = 1")

    assert run_python_file(sandbox, "quiet.py") == "No output produced"


def test_nonzero_exit_is_reported(sandbox, write):
    """Assert a nonzero exit code is surfaced in the result"""
    write("fail.py", "import sys\nsys.exit(3)")

    result = run_python_file(sandbox, "fail.py")

    assert result.startswith("Process exited with code 3")


def test_stderr_is_captured(sandbox, write):
    """Assert an uncaught exception is reported with its exit code and STDERR"""
    write("boom.py", "raise ValueError('kaboom')")

    result = run_python_file(sandbox, "boom.py")

    assert "Process exited with code 1" in result
    assert "STDERR:" in result
    assert "kaboom" in result


def test_stdout_and_stderr_are_both_reported(sandbox, write):
    """Assert both streams appear when the script writes to each"""
    write("both.py", "import sys\nprint('out')\nprint('err', file=sys.stderr)")

    result = run_python_file(sandbox, "both.py")

    assert "STDOUT: out\n" in result
    assert "STDERR: err\n" in result


def test_file_outside_the_sandbox_is_refused(sandbox):
    """Assert a path outside the sandbox is refused before anything runs"""
    result = run_python_file(sandbox, "../main.py")

    assert result == 'Error: Cannot execute "../main.py" as it is outside the permitted working directory'


def test_missing_file_is_reported(sandbox):
    """Assert a nonexistent script returns the not-a-regular-file error"""
    result = run_python_file(sandbox, "nonexistent.py")

    assert result == 'Error: "nonexistent.py" does not exist or is not a regular file'


def test_non_python_file_is_refused(sandbox, write):
    """Assert a file without a .py extension is refused"""
    write("lorem.txt", "lorem ipsum")

    assert run_python_file(sandbox, "lorem.txt") == 'Error: "lorem.txt" is not a Python file'


def test_directory_is_rejected_before_the_extension_check(sandbox, write):
    """Assert a directory fails the regular-file check, not the extension check"""
    write("pkg/calculator.py", "x")

    assert run_python_file(sandbox, "pkg") == 'Error: "pkg" does not exist or is not a regular file'
