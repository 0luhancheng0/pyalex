#!/usr/bin/env python3
"""
Tests for PyAlex CLI
"""

import json
import os
import subprocess
import tempfile
from typing import Any

import pytest  # type: ignore[import-not-found]
from click.testing import CliRunner


def test_cli_help():
    """Test that the CLI help command works."""
    result = subprocess.run(["pyalex", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "CLI interface for the OpenAlex database" in result.stdout


def test_works_help():
    """Test that the works subcommand help works."""
    result = subprocess.run(
        ["pyalex", "works", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Search and retrieve works from OpenAlex" in result.stdout


def test_authors_help():
    """Test that the authors subcommand help works."""
    result = subprocess.run(
        ["pyalex", "authors", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Search and retrieve authors from OpenAlex" in result.stdout


def test_topics_help():
    """Test that the topics subcommand help works."""
    result = subprocess.run(
        ["pyalex", "topics", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Search and retrieve topics from OpenAlex" in result.stdout


def test_concepts_help():
    """Test that the concepts subcommand help works."""
    result = subprocess.run(
        ["pyalex", "concepts", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Search and retrieve concepts from OpenAlex" in result.stdout


def test_keywords_help():
    """Test that the keywords subcommand help works."""
    result = subprocess.run(
        ["pyalex", "keywords", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Search and retrieve keywords from OpenAlex" in result.stdout


def test_show_help():
    """Test that the show subcommand help works."""
    result = subprocess.run(
        ["pyalex", "show", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Display a JSON or Parquet file containing OpenAlex data" in result.stdout


def test_works_search():
    """Test that works search returns results."""
    result = subprocess.run(
        ["pyalex", "works", "--search", "test", "--limit", "1"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # Should contain some data or status message
    assert len(result.stdout.strip()) > 0


def test_works_summary_format():
    """Test that works search returns table format by default."""
    result = subprocess.run(
        ["pyalex", "works", "--search", "test", "--limit", "1"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # Should show table format with headers
    assert "Name" in result.stdout or "ID" in result.stdout


def test_works_select_fields_table_header():
    """Works select should use selected fields as table headers."""
    result = subprocess.run(
        [
            "pyalex",
            "works",
            "--select",
            "title,fwci",
            "--limit",
            "1",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    header_line = next(
        (line for line in result.stdout.splitlines() if line.startswith("|")),
        "",
    )
    assert "| id" in header_line
    assert "| title" in header_line
    assert "| fwci" in header_line
    assert "| Name" not in header_line


def test_works_select_abstract_requests_inverted_index(monkeypatch):
    """Selecting abstract should implicitly fetch the inverted index field."""

    from pyalex.cli import main as cli_main
    from pyalex.cli.commands import works as works_module

    monkeypatch.setattr(
        works_module,
        "handle_large_id_list_if_needed",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        works_module,
        "execute_standard_query",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        works_module,
        "_output_results",
        lambda *_args, **_kwargs: None,
    )

    class DummyWorks:
        last_instance: "DummyWorks | None" = None

        def __init__(self):
            self.selected_fields: list[str] | None = None
            type(self).last_instance = self

        def search(self, *_args, **_kwargs):
            return self

        def filter(self, **_kwargs):
            return self

        def sort(self, **_kwargs):
            return self

        def select(self, fields):
            self.selected_fields = fields
            return self

        def sample(self, *_args, **_kwargs):
            return self

    monkeypatch.setattr(works_module, "Works", DummyWorks)

    from typer.main import get_command

    runner = CliRunner()
    result = runner.invoke(
        get_command(cli_main.app),
        ["works", "--select", "title,abstract", "--limit", "1"],
    )

    assert result.exit_code == 0, result.stdout or result.stderr
    assert DummyWorks.last_instance is not None
    assert DummyWorks.last_instance.selected_fields is not None
    assert DummyWorks.last_instance.selected_fields == [
        "id",
        "title",
        "abstract_inverted_index",
    ]


def test_works_select_title_abstract_template(monkeypatch):
    """Selecting title_abstract should fetch dependencies and apply template."""

    from pyalex import config as global_config
    from pyalex.cli import main as cli_main
    from pyalex.cli import utils as cli_utils
    from pyalex.cli.commands import works as works_module

    template = "Title: {title} | Abstract: {abstract}"
    monkeypatch.setattr(global_config, "title_abstract_template", template)

    captured_table: dict[str, Any] = {}

    def capture_table(results, single=False, grouped=False, selected_fields=None):
        captured_table["results"] = results
        captured_table["single"] = single
        captured_table["grouped"] = grouped
        captured_table["selected_fields"] = selected_fields

    monkeypatch.setattr(cli_utils, "_output_table", capture_table)
    monkeypatch.setattr(
        works_module,
        "handle_large_id_list_if_needed",
        lambda *_args, **_kwargs: None,
    )

    def fake_execute_standard_query(*_args, **_kwargs):
        return [
            {
                "id": "https://openalex.org/W123",
                "title": "Sample Title",
                "abstract_inverted_index": {
                    "sample": [0],
                    "abstract": [1],
                },
            }
        ]

    monkeypatch.setattr(
        works_module,
        "execute_standard_query",
        fake_execute_standard_query,
    )

    class DummyWorks:
        last_instance: "DummyWorks | None" = None

        def __init__(self):
            self.selected_fields: list[str] | None = None
            type(self).last_instance = self

        def search(self, *_args, **_kwargs):
            return self

        def filter(self, **_kwargs):
            return self

        def sort(self, **_kwargs):
            return self

        def select(self, fields):
            self.selected_fields = fields
            return self

        def sample(self, *_args, **_kwargs):
            return self

        def get(self, *_args, **_kwargs):
            return []

    monkeypatch.setattr(works_module, "Works", DummyWorks)

    from typer.main import get_command

    runner = CliRunner()
    result = runner.invoke(
        get_command(cli_main.app),
        ["works", "--select", "title_abstract", "--limit", "1"],
    )

    assert result.exit_code == 0, result.stdout or result.stderr
    assert DummyWorks.last_instance is not None
    assert DummyWorks.last_instance.selected_fields == [
        "id",
        "title",
        "abstract_inverted_index",
    ]
    assert captured_table["selected_fields"] == ["id", "title_abstract"]
    assert captured_table["grouped"] is False
    assert isinstance(captured_table["results"], list)
    assert captured_table["results"][0]["title_abstract"] == (
        "Title: Sample Title | Abstract: sample abstract"
    )


def test_works_json_outputs_jsonl(monkeypatch, tmp_path):
    """--jsonl and --jsonl-file should emit newline-delimited JSON records."""

    from pyalex.cli import main as cli_main
    from pyalex.cli.commands import works as works_module

    monkeypatch.setattr(
        works_module,
        "handle_large_id_list_if_needed",
        lambda *_args, **_kwargs: None,
    )

    sample_results = [
        {
            "id": "https://openalex.org/W1",
            "title": "First Work",
            "abstract_inverted_index": None,
        },
        {
            "id": "https://openalex.org/W2",
            "title": "Second Work",
            "abstract_inverted_index": None,
        },
    ]

    monkeypatch.setattr(
        works_module,
        "execute_standard_query",
        lambda *_args, **_kwargs: sample_results,
    )

    class DummyWorks:
        def __init__(self):
            self.selected_fields: list[str] | None = None

        def search(self, *_args, **_kwargs):
            return self

        def filter(self, **_kwargs):
            return self

        def sort(self, **_kwargs):
            return self

        def select(self, fields):
            self.selected_fields = fields
            return self

        def sample(self, *_args, **_kwargs):
            return self

    monkeypatch.setattr(works_module, "Works", DummyWorks)

    from typer.main import get_command

    output_path = tmp_path / "works.jsonl"
    runner = CliRunner()

    # File output
    result_file = runner.invoke(
        get_command(cli_main.app),
        [
            "works",
            "--limit",
            "2",
            "--jsonl-file",
            str(output_path),
        ],
    )

    assert result_file.exit_code == 0, result_file.stdout or result_file.stderr
    file_lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(file_lines) == 2
    parsed_file = [json.loads(line) for line in file_lines]
    assert parsed_file[0]["id"].endswith("W1")
    assert parsed_file[1]["id"].endswith("W2")

    # Stdout output
    result_stdout = runner.invoke(
        get_command(cli_main.app),
        ["works", "--limit", "2", "--jsonl"],
    )

    assert result_stdout.exit_code == 0, result_stdout.stdout or result_stdout.stderr
    stdout_lines = [line for line in result_stdout.stdout.splitlines() if line]
    assert len(stdout_lines) == 2
    parsed_stdout = [json.loads(line) for line in stdout_lines]
    assert parsed_stdout[0]["id"].endswith("W1")
    assert parsed_stdout[1]["id"].endswith("W2")


def test_works_normalize_option_sets_flag(monkeypatch):
    """--normalize should request flattened output from the utilities layer."""

    from pyalex.cli import main as cli_main
    from pyalex.cli.commands import works as works_module

    monkeypatch.setattr(
        works_module,
        "handle_large_id_list_if_needed",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        works_module,
        "execute_standard_query",
        lambda *_args, **_kwargs: [],
    )

    captured: dict[str, Any] = {}

    def capture_output(
        _results,
        _jsonl_path=None,
        _parquet_path=None,
        **kwargs,
    ):
        captured["normalize"] = kwargs.get("normalize")

    monkeypatch.setattr(works_module, "_output_results", capture_output)

    from typer.main import get_command

    runner = CliRunner()
    result = runner.invoke(
        get_command(cli_main.app),
        ["works", "--limit", "1", "--normalize"],
    )

    assert result.exit_code == 0, result.stdout or result.stderr
    assert captured.get("normalize") is True


def test_institutions_select_fields_table_header():
    """Institutions select should replace default columns with requested ones."""
    result = subprocess.run(
        [
            "pyalex",
            "institutions",
            "--select",
            "display_name,works_count",
            "--limit",
            "1",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    header_line = next(
        (line for line in result.stdout.splitlines() if line.startswith("|")),
        "",
    )
    assert "| id" in header_line
    assert "| display_name" in header_line
    assert "| works_count" in header_line
    assert "| Name" not in header_line


def test_show_json_file():
    """Test that show command works with JSON files."""
    # Create a temporary JSON file with sample data
    sample_data = [
        {
            "id": "https://openalex.org/W1234567890",
            "display_name": "Test Work",
            "publication_year": 2023,
            "cited_by_count": 42,
            "primary_location": {"source": {"display_name": "Test Journal"}},
        }
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_data, f)
        temp_file = f.name

    try:
        # Test show command (table format is default)
        result = subprocess.run(
            ["pyalex", "show", temp_file], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "Test Work" in result.stdout

    finally:
        # Clean up temp file
        os.unlink(temp_file)


def test_show_nonexistent_file():
    """Test that show command handles nonexistent files gracefully."""
    result = subprocess.run(
        ["pyalex", "show", "nonexistent_file.json"], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "not found" in result.stderr


def test_works_publication_date():
    """Test that works search with publication date filter works."""
    result = subprocess.run(
        ["pyalex", "works", "--date", "2020-01-01", "--limit", "1"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # Should return some output (table or other format)
    assert len(result.stdout.strip()) > 0


def test_works_publication_date_range():
    """Test that works search with publication date range filter works."""
    result = subprocess.run(
        ["pyalex", "works", "--date", "2020-01-01:2020-01-31", "--limit", "1"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # Should return some output (table or other format)
    assert len(result.stdout.strip()) > 0


def test_works_publication_date_invalid():
    """Test that works search with invalid publication date fails."""
    result = subprocess.run(
        ["pyalex", "works", "--date", "invalid-date", "--limit", "1"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Invalid date format" in result.stderr


def test_works_publication_date_invalid_range():
    """Test that works search with invalid publication date range fails."""
    result = subprocess.run(
        ["pyalex", "works", "--date", "2020-13-01:2020-14-01", "--limit", "1"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Invalid date range format" in result.stderr


@pytest.mark.parametrize(
    ("option_name", "filter_key", "payload", "expected"),
    [
        (
            "--author-ids",
            "works_author",
            '[{"id": "https://openalex.org/A123"}, {"id": "A456"}]\n',
            "A123,A456",
        ),
        (
            "--institution-ids",
            "works_institution",
            '[{"id": "https://openalex.org/I123"}, {"id": "I456"}]\n',
            "I123,I456",
        ),
        (
            "--topic-ids",
            "works_topic",
            '[{"id": "https://openalex.org/T123"}, {"id": "T456"}]\n',
            "T123,T456",
        ),
        (
            "--subfield-ids",
            "works_subfield",
            '[{"id": "https://openalex.org/SF123"}, {"id": "SF456"}]\n',
            "SF123,SF456",
        ),
        (
            "--funder-ids",
            "works_funder",
            '[{"id": "https://openalex.org/F123"}, {"id": "F456"}]\n',
            "F123,F456",
        ),
        (
            "--award-ids",
            "works_award",
            '["AWARD123", "AWARD456"]\n',
            "AWARD123,AWARD456",
        ),
        (
            "--source-ids",
            "works_source",
            '[{"id": "https://openalex.org/S123"}, {"id": "S456"}]\n',
            "S123,S456",
        ),
        (
            "--host-venue-ids",
            "works_host_venue",
            '[{"id": "https://openalex.org/S789"}, {"id": "S321"}]\n',
            "S789,S321",
        ),
        (
            "--source-issn",
            "works_source_issn",
            '[{"issn": "1234-5678"}, {"issn": "8765-4321"}]\n',
            "1234-5678,8765-4321",
        ),
        (
            "--source-host-org-ids",
            "works_source_host_org",
            '[{"id": "https://openalex.org/P123"}, {"id": "P456"}]\n',
            "P123,P456",
        ),
        (
            "--cited-by",
            "works_cited_by",
            '[{"id": "https://openalex.org/W123"}, {"id": "W456"}]\n',
            "W123,W456",
        ),
        (
            "--cites",
            "works_cites",
            '[{"id": "https://openalex.org/W789"}, {"id": "W654"}]\n',
            "W789,W654",
        ),
    ],
)
def test_works_ids_from_stdin(monkeypatch, option_name, filter_key, payload, expected):
    """Works command should parse ID options from stdin when no value is given."""

    from pyalex.cli import main as cli_main
    from pyalex.cli.commands import works as works_module

    recorded: dict[str, str] = {}

    def fake_add_id_list_option_to_command(
        query, option_value: str, filter_config_key: str, entity_class
    ):
        recorded["option_value"] = option_value
        recorded["filter_config_key"] = filter_config_key
        recorded["entity_class"] = (
            entity_class.__name__
            if hasattr(entity_class, "__name__")
            else str(entity_class)
        )
        return query

    monkeypatch.setattr(
        works_module,
        "add_id_list_option_to_command",
        fake_add_id_list_option_to_command,
    )
    monkeypatch.setattr(
        works_module,
        "parse_select_fields",
        lambda _select: None,
    )
    monkeypatch.setattr(
        works_module,
        "_validate_and_apply_common_options",
        lambda query, *_args, **_kwargs: query,
    )
    monkeypatch.setattr(
        works_module,
        "handle_large_id_list_if_needed",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        works_module,
        "execute_standard_query",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        works_module,
        "_output_results",
        lambda *_args, **_kwargs: None,
    )

    class DummyWorks:
        def __init__(self):
            self.params: dict[str, dict[str, str]] = {}

        def search(self, *_args, **_kwargs):
            return self

        def filter(self, **kwargs):
            self.params.setdefault("filter", {}).update(kwargs)
            return self

    monkeypatch.setattr(works_module, "Works", DummyWorks)

    from typer.main import get_command

    runner = CliRunner()
    result = runner.invoke(
        get_command(cli_main.app),
        ["works", option_name, "--limit", "1"],
        input=payload,
    )

    assert result.exit_code == 0, result.stdout or result.stderr
    assert recorded["option_value"] == expected
    assert recorded["filter_config_key"] == filter_key
    assert recorded["entity_class"] == "DummyWorks"


@pytest.mark.parametrize(
    ("option_args", "expected_kwargs"),
    [
        (["--is-oa"], {"is_oa": True}),
        (["--not-oa"], {"is_oa": False}),
        (["--oa-status", "gold"], {"oa_status": "gold"}),
    ],
)
def test_works_open_access_flags(monkeypatch, option_args, expected_kwargs):
    """Works CLI should apply open access filters from boolean and status flags."""

    from pyalex.cli import main as cli_main
    from pyalex.cli.commands import works as works_module

    recorded: dict[str, list[dict[str, str | bool]]] = {"oa": []}

    class DummyWorks:
        def __init__(self):
            self.params: dict[str, dict[str, str]] = {}

        def search(self, *_args, **_kwargs):
            return self

        def filter_by_open_access(self, **kwargs):
            recorded.setdefault("oa", []).append(kwargs)
            return self

        def filter(self, **kwargs):
            recorded.setdefault("filters", []).append(kwargs)
            return self

    monkeypatch.setattr(works_module, "Works", DummyWorks)
    monkeypatch.setattr(
        works_module,
        "add_id_list_option_to_command",
        lambda query, *_args, **_kwargs: query,
    )
    monkeypatch.setattr(
        works_module,
        "parse_select_fields",
        lambda _select: None,
    )
    monkeypatch.setattr(
        works_module,
        "_validate_and_apply_common_options",
        lambda query, *_args, **_kwargs: query,
    )
    monkeypatch.setattr(
        works_module,
        "handle_large_id_list_if_needed",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        works_module,
        "execute_standard_query",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        works_module,
        "_output_results",
        lambda *_args, **_kwargs: None,
    )

    from typer.main import get_command

    runner = CliRunner()
    result = runner.invoke(
        get_command(cli_main.app),
        ["works", *option_args, "--limit", "1"],
    )

    assert result.exit_code == 0, result.stdout or result.stderr
    assert recorded["oa"], "Expected filter_by_open_access to be called"
    assert recorded["oa"][-1] == expected_kwargs


def test_works_content_filters(monkeypatch):
    """Works CLI should map abstract and fulltext flags to filters."""

    from pyalex.cli import main as cli_main
    from pyalex.cli.commands import works as works_module

    recorded: dict[str, list] = {"filters": []}

    class DummyWorks:
        def __init__(self):
            self.params: dict[str, dict[str, str]] = {}

        def search(self, *_args, **_kwargs):
            return self

        def filter(self, **kwargs):
            recorded.setdefault("filters", []).append(kwargs)
            return self

        def filter_by_open_access(self, **_kwargs):
            return self

        def filter_by_abstract_search(self, term, **_kwargs):
            recorded["abstract"] = term
            return self

    monkeypatch.setattr(works_module, "Works", DummyWorks)
    monkeypatch.setattr(
        works_module,
        "add_id_list_option_to_command",
        lambda query, *_args, **_kwargs: query,
    )
    monkeypatch.setattr(
        works_module,
        "parse_select_fields",
        lambda _select: None,
    )
    monkeypatch.setattr(
        works_module,
        "_validate_and_apply_common_options",
        lambda query, *_args, **_kwargs: query,
    )
    monkeypatch.setattr(
        works_module,
        "handle_large_id_list_if_needed",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        works_module,
        "execute_standard_query",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        works_module,
        "_output_results",
        lambda *_args, **_kwargs: None,
    )

    from typer.main import get_command

    runner = CliRunner()
    result = runner.invoke(
        get_command(cli_main.app),
        [
            "works",
            "--has-abstract",
            "--no-fulltext",
            "--abstract-search",
            "graphene",
            "--limit",
            "1",
        ],
    )

    assert result.exit_code == 0, result.stdout or result.stderr
    assert {"has_abstract": True} in recorded["filters"]
    assert {"has_fulltext": False} in recorded["filters"]
    assert recorded["abstract"] == "graphene"

def test_authors_institution_ids_from_stdin(monkeypatch):
    """Authors command should read institution IDs from stdin when omitted."""

    from pyalex.cli import main as cli_main
    from pyalex.cli.commands import authors as authors_module

    recorded: dict[str, str] = {}

    def fake_add_id_list_option_to_command(
        query, option_value: str, filter_config_key: str, entity_class
    ):
        recorded["option_value"] = option_value
        recorded["filter_config_key"] = filter_config_key
        recorded["entity_class"] = (
            entity_class.__name__
            if hasattr(entity_class, "__name__")
            else str(entity_class)
        )
        return query

    monkeypatch.setattr(
        authors_module,
        "add_id_list_option_to_command",
        fake_add_id_list_option_to_command,
    )
    monkeypatch.setattr(
        authors_module,
        "parse_select_fields",
        lambda _select: None,
    )
    monkeypatch.setattr(
        authors_module,
        "_validate_and_apply_common_options",
        lambda query, *_args, **_kwargs: query,
    )
    monkeypatch.setattr(
        authors_module,
        "handle_large_id_list_if_needed",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        authors_module,
        "execute_standard_query",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        authors_module,
        "_output_results",
        lambda *_args, **_kwargs: None,
    )

    class DummyAuthors:
        def __init__(self):
            self.params: dict[str, dict[str, str]] = {}

        def search(self, *_args, **_kwargs):
            return self

        def filter(self, **kwargs):
            self.params.setdefault("filter", {}).update(kwargs)
            return self

    monkeypatch.setattr(authors_module, "Authors", DummyAuthors)

    from typer.main import get_command

    runner = CliRunner()
    payload = '[{"id": "https://openalex.org/I123"}, {"id": "I456"}]\n'
    result = runner.invoke(
        get_command(cli_main.app),
        ["authors", "--institution-ids", "--limit", "1"],
        input=payload,
    )

    assert result.exit_code == 0, result.stdout or result.stderr
    assert recorded["option_value"] == "I123,I456"
    assert recorded["filter_config_key"] == "authors_institution"
    assert recorded["entity_class"] == "DummyAuthors"


def test_authors_institution_rors_from_stdin(monkeypatch):
    """Authors command should normalize ROR identifiers from stdin input."""

    from pyalex.cli import main as cli_main
    from pyalex.cli.commands import authors as authors_module

    recorded: list[tuple[str, str]] = []

    def fake_add_id_list_option_to_command(
        query, option_value: str, filter_config_key: str, _entity_class
    ):
        recorded.append((filter_config_key, option_value))
        return query

    monkeypatch.setattr(
        authors_module,
        "add_id_list_option_to_command",
        fake_add_id_list_option_to_command,
    )
    monkeypatch.setattr(
        authors_module,
        "parse_select_fields",
        lambda _select: None,
    )
    monkeypatch.setattr(
        authors_module,
        "_validate_and_apply_common_options",
        lambda query, *_args, **_kwargs: query,
    )
    monkeypatch.setattr(
        authors_module,
        "handle_large_id_list_if_needed",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        authors_module,
        "execute_standard_query",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        authors_module,
        "_output_results",
        lambda *_args, **_kwargs: None,
    )

    class DummyAuthors:
        def __init__(self):
            self.params: dict[str, dict[str, str]] = {}

        def search(self, *_args, **_kwargs):
            return self

    monkeypatch.setattr(authors_module, "Authors", DummyAuthors)

    from typer.main import get_command

    payload = '[{"ror": "01an7q238"}, {"ror": "https://ror.org/05abcde12"}]\n'

    runner = CliRunner()
    result = runner.invoke(
        get_command(cli_main.app),
        ["authors", "--institution-rors", "--limit", "1"],
        input=payload,
    )

    assert result.exit_code == 0, result.stdout or result.stderr
    expected_call = (
        "authors_institution_ror",
        "https://ror.org/01an7q238,https://ror.org/05abcde12",
    )
    assert expected_call in recorded


def test_authors_presence_flags(monkeypatch):
    """Authors CLI should map presence flags to boolean filters."""

    from pyalex.cli import main as cli_main
    from pyalex.cli.commands import authors as authors_module

    recorded: list[dict[str, bool]] = []

    class DummyAuthors:
        def __init__(self):
            self.params: dict[str, dict[str, str]] = {}

        def search(self, *_args, **_kwargs):
            return self

        def filter(self, **kwargs):
            recorded.append(kwargs)
            return self

    monkeypatch.setattr(authors_module, "Authors", DummyAuthors)
    monkeypatch.setattr(
        authors_module,
        "add_id_list_option_to_command",
        lambda query, *_args, **_kwargs: query,
    )
    monkeypatch.setattr(
        authors_module,
        "parse_select_fields",
        lambda _select: None,
    )
    monkeypatch.setattr(
        authors_module,
        "_validate_and_apply_common_options",
        lambda query, *_args, **_kwargs: query,
    )
    monkeypatch.setattr(
        authors_module,
        "handle_large_id_list_if_needed",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        authors_module,
        "execute_standard_query",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        authors_module,
        "_output_results",
        lambda *_args, **_kwargs: None,
    )

    from typer.main import get_command

    runner = CliRunner()
    result = runner.invoke(
        get_command(cli_main.app),
        [
            "authors",
            "--has-orcid",
            "--has-twitter",
            "--no-wikipedia",
            "--limit",
            "1",
        ],
    )

    assert result.exit_code == 0, result.stdout or result.stderr
    assert {"has_orcid": True} in recorded
    assert {"has_twitter": True} in recorded
    assert {"has_wikipedia": False} in recorded

def test_works_cited_by_count_range(monkeypatch):
    """Works command should apply range filter for cited-by-count option."""

    from pyalex.cli import main as cli_main
    from pyalex.cli.commands import works as works_module

    recorded: dict[str, str] = {}

    def fake_parse_range_filter(value):
        recorded["input_value"] = value
        return "parsed-range"

    def fake_apply_range_filter(query, field, parsed_value):
        recorded["field"] = field
        recorded["parsed_value"] = parsed_value
        return query

    monkeypatch.setattr(works_module, "parse_range_filter", fake_parse_range_filter)
    monkeypatch.setattr(works_module, "apply_range_filter", fake_apply_range_filter)
    monkeypatch.setattr(
        works_module,
        "parse_select_fields",
        lambda _select: None,
    )
    monkeypatch.setattr(
        works_module,
        "_validate_and_apply_common_options",
        lambda query, *_args, **_kwargs: query,
    )
    monkeypatch.setattr(
        works_module,
        "handle_large_id_list_if_needed",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        works_module,
        "execute_standard_query",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        works_module,
        "_output_results",
        lambda *_args, **_kwargs: None,
    )

    class DummyWorks:
        def __init__(self):
            self.params: dict[str, dict[str, str]] = {}

        def search(self, *_args, **_kwargs):
            return self

        def filter(self, **kwargs):
            self.params.setdefault("filter", {}).update(kwargs)
            return self

    monkeypatch.setattr(works_module, "Works", DummyWorks)

    from typer.main import get_command

    runner = CliRunner()
    result = runner.invoke(
        get_command(cli_main.app),
        ["works", "--cited-by-count", "100:200", "--limit", "1"],
    )

    assert result.exit_code == 0, result.stdout or result.stderr
    assert recorded["input_value"] == "100:200"
    assert recorded["field"] == "cited_by_count"
    assert recorded["parsed_value"] == "parsed-range"


if __name__ == "__main__":
    pytest.main([__file__])
