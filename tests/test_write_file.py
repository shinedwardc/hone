import os

from hone.tools.write_file import write_file


def test_creates_a_file_and_reports_the_character_count(sandbox):
    """Assert a new file is written and the reported count matches the content"""
    result = write_file(sandbox, "notes.txt", "hello")

    assert result == 'Successfully wrote to "notes.txt" (5 characters written)'
    with open(os.path.join(sandbox, "notes.txt"), encoding="utf-8") as file:
        assert file.read() == "hello"


def test_overwrites_existing_content(sandbox, write):
    """Assert an existing file is replaced, not appended to"""
    write("lorem.txt", "lorem ipsum dolor sit amet")

    write_file(sandbox, "lorem.txt", "wait, this isn't lorem ipsum")

    with open(os.path.join(sandbox, "lorem.txt"), encoding="utf-8") as file:
        assert file.read() == "wait, this isn't lorem ipsum"


def test_creates_missing_parent_directories(sandbox):
    """Assert missing parent directories are created on the way"""
    result = write_file(sandbox, "pkg/nested/deep.txt", "content")

    assert result.startswith("Successfully wrote to")
    assert os.path.isfile(os.path.join(sandbox, "pkg", "nested", "deep.txt"))


def test_writes_empty_content(sandbox):
    """Assert empty content writes a zero-byte file, not an error"""
    result = write_file(sandbox, "empty.txt", "")

    assert result == 'Successfully wrote to "empty.txt" (0 characters written)'
    assert os.path.getsize(os.path.join(sandbox, "empty.txt")) == 0


def test_character_count_reflects_the_content_length(sandbox):
    """Assert the reported count is the length of the content written"""
    content = "a" * 1234

    result = write_file(sandbox, "big.txt", content)

    assert "(1234 characters written)" in result


def test_absolute_path_outside_the_sandbox_is_refused(sandbox, tmp_path):
    """Assert an absolute path outside the sandbox is refused and nothing is written"""
    outside = tmp_path.parent / "outside_target.txt"

    result = write_file(sandbox, str(outside), "this should not be allowed")

    assert result == f'Error: Cannot write to "{outside}" as it is outside the permitted working directory'
    assert not outside.exists()


def test_parent_traversal_is_refused(sandbox, tmp_path):
    """Assert a path climbing above the sandbox root is refused and nothing is written"""
    result = write_file(sandbox, "../escaped.txt", "nope")

    assert result == 'Error: Cannot write to "../escaped.txt" as it is outside the permitted working directory'
    assert not (tmp_path.parent / "escaped.txt").exists()


def test_writing_over_a_directory_is_refused(sandbox):
    """Assert an existing directory is not clobbered by a write"""
    os.makedirs(os.path.join(sandbox, "pkg"))

    result = write_file(sandbox, "pkg", "content")

    assert result == 'Error: Cannot write to "pkg" as it is a directory'
    assert os.path.isdir(os.path.join(sandbox, "pkg"))
