import datetime
import pytest
from click.testing import CliRunner
from pyalex.cli import main as cli_main
from pyalex.cli.commands import works as works_module

def test_works_relative_date_filter(monkeypatch):
    """Works CLI should handle relative date format like '-7d:' correctly."""

    recorded: dict[str, dict] = {"date_filters": {}}

    class DummyWorks:
        def __init__(self):
            self.params: dict[str, dict[str, str]] = {}

        def search(self, *_args, **_kwargs):
            return self

        def filter_by_publication_date(self, **kwargs):
            recorded["date_filters"] = kwargs
            return self
            
        def filter(self, **kwargs):
            return self
            
        def filter_by_open_access(self, **kwargs):
            return self

    monkeypatch.setattr(works_module, "Works", DummyWorks)
    
    # Mock other dependencies to prevent execution of actual logic
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
    
    # Test case: "-7d:"
    result = runner.invoke(
        get_command(cli_main.app),
        [
            "works",
            "--date",
            "-7d:",
            "--limit",
            "1",
        ],
    )

    assert result.exit_code == 0, result.stdout or result.stderr
    
    # Calculate expected dates
    today = datetime.date.today()
    expected_start = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    expected_end = today.strftime("%Y-%m-%d")
    
    assert recorded["date_filters"]["start_date"] == expected_start
    assert recorded["date_filters"]["end_date"] == expected_end

def test_works_relative_date_filter_specific_end(monkeypatch):
    """Works CLI should handle relative date format with specific end like '-7d:2025-01-01'."""

    recorded: dict[str, dict] = {"date_filters": {}}

    class DummyWorks:
        def __init__(self):
            self.params: dict[str, dict[str, str]] = {}

        def search(self, *_args, **_kwargs):
            return self

        def filter_by_publication_date(self, **kwargs):
            recorded["date_filters"] = kwargs
            return self

        def filter(self, **kwargs):
            return self
            
        def filter_by_open_access(self, **kwargs):
            return self

    monkeypatch.setattr(works_module, "Works", DummyWorks)
    
    # Mock dependencies
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
    
    # Test case: "-7d:2025-01-01"
    # Note: validation will fail if start_date (calculated relative to today) > end_date (2025-01-01) depending on current date.
    # But current logic doesn't validate start <= end inside the command, only formatting.
    # So this test mainly checks if "-7d" is parsed correctly.
    
    result = runner.invoke(
        get_command(cli_main.app),
        [
            "works",
            "--date",
            "-7d:2025-01-01",
            "--limit",
            "1",
        ],
    )

    assert result.exit_code == 0, result.stdout or result.stderr
    
    today = datetime.date.today()
    expected_start = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    
    assert recorded["date_filters"]["start_date"] == expected_start
    assert recorded["date_filters"]["end_date"] == "2025-01-01"

def test_works_invalid_relative_date_format(monkeypatch):
    """Works CLI should show updated error message for invalid date format."""

    monkeypatch.setattr(works_module, "Works", type("Dummy", (), {}))
    
    # Mock dependencies
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
    
    # Test case: "-7x:" (invalid unit)
    result = runner.invoke(
        get_command(cli_main.app),
        [
            "works",
            "--date",
            "-7x:",
            "--limit",
            "1",
        ],
    )

    assert result.exit_code == 1
    assert "Invalid date range format" in result.stderr
    assert "relative format" in result.stderr

if __name__ == "__main__":
    pytest.main([__file__])
