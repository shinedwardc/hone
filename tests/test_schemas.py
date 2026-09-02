"""The schemas are what the model sees; a drifted name or type breaks tool calls."""

import pytest

from hone.tools.ask_user import ask_user, schema_ask_user
from hone.tools.list_dir import get_files_info, schema_get_files_info
from hone.tools.read_file import get_file_content, schema_get_file_content
from hone.tools.run_python import run_python_file, schema_run_python_file
from hone.tools.write_file import schema_write_file, write_file

SCHEMAS = [
    (schema_get_files_info, get_files_info, ()),
    (schema_get_file_content, get_file_content, ("file_path",)),
    (schema_run_python_file, run_python_file, ("file_path",)),
    (schema_write_file, write_file, ("file_path", "content")),
    (schema_ask_user, ask_user, ("question",)),
]

IDS = [schema["function"]["name"] for schema, _, _ in SCHEMAS]


@pytest.mark.parametrize("schema, function, required", SCHEMAS, ids=IDS)
def test_schema_name_matches_the_python_function(schema, function, required):
    """Assert each schema is a function schema named after its Python function"""
    assert schema["type"] == "function"
    assert schema["function"]["name"] == function.__name__


@pytest.mark.parametrize("schema, function, required", SCHEMAS, ids=IDS)
def test_schema_declares_its_required_parameters(schema, function, required):
    """Assert the schema's required list matches the parameters the tool needs"""
    assert tuple(schema["function"]["parameters"].get("required", ())) == required


@pytest.mark.parametrize("schema, function, required", SCHEMAS, ids=IDS)
def test_declared_parameters_exist_on_the_function(schema, function, required):
    """Assert every declared parameter is accepted, and working_directory is never exposed"""
    declared = set(schema["function"]["parameters"]["properties"])
    accepted = set(function.__code__.co_varnames[: function.__code__.co_argcount])

    assert declared <= accepted
    # working_directory is supplied by the dispatcher, never by the model.
    assert "working_directory" not in declared


@pytest.mark.parametrize("schema, function, required", SCHEMAS, ids=IDS)
def test_every_parameter_is_typed_and_described(schema, function, required):
    """Assert the schema and each of its parameters carry a type and a description"""
    parameters = schema["function"]["parameters"]

    assert parameters["type"] == "object"
    assert schema["function"]["description"]
    for name, spec in parameters["properties"].items():
        assert spec["type"], f"{name} has no type"
        assert spec["description"], f"{name} has no description"
