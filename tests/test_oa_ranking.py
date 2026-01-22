
import pytest
from click.testing import CliRunner
from pyalex.cli import main as cli_main
from pyalex.cli.commands import works as works_module

def test_works_oa_status_range_ranking(monkeypatch):
    """Verify that oa-status ranges respect the new ranking: closed < bronze < hybrid < green < gold < diamond."""
    
    recorded_kwargs = {}

    class DummyWorks:
        def __init__(self):
            pass

        def search(self, *_args, **_kwargs):
            return self

        def filter_by_open_access(self, **kwargs):
            recorded_kwargs.update(kwargs)
            return self
            
        def filter(self, **kwargs):
            return self

        def group_by(self, *args, **kwargs):
            return self

    monkeypatch.setattr(works_module, "Works", DummyWorks)
    
    # Mock other dependencies to avoid side effects
    monkeypatch.setattr(works_module, "validate_pagination_options", lambda *args: None)
    monkeypatch.setattr(works_module, "validate_output_format_options", lambda *args: (None, None))
    monkeypatch.setattr(works_module, "handle_large_id_list_if_needed", lambda *args, **kwargs: None)
    monkeypatch.setattr(works_module, "execute_standard_query", lambda *args, **kwargs: [])
    monkeypatch.setattr(works_module, "_output_results", lambda *args, **kwargs: None)
    monkeypatch.setattr(works_module, "_validate_and_apply_common_options", lambda query, *args, **kwargs: query)

    runner = CliRunner()
    
    # Test case 1: hybrid:gold -> should be hybrid|green|gold (since hybrid < green < gold)
    # Ranks: closed(0), bronze(1), hybrid(2), green(3), gold(4), diamond(5)
    recorded_kwargs.clear()
    result = runner.invoke(
        cli_main.app, 
        ["works", "--oa-status", "hybrid:gold"]
    )
    assert result.exit_code == 0
    # hybrid(2) to gold(4) -> [hybrid, green, gold]
    assert recorded_kwargs["oa_status"] == "hybrid|green|gold"

    # Test case 2: green:gold -> should be green|gold (since green(3) < gold(4))
    recorded_kwargs.clear()
    result = runner.invoke(
        cli_main.app, 
        ["works", "--oa-status", "green:gold"]
    )
    assert result.exit_code == 0
    # green(3) to gold(4) -> [green, gold]
    assert recorded_kwargs["oa_status"] == "green|gold"

    # Test case 3: bronze:hybrid -> should be bronze|hybrid
    recorded_kwargs.clear()
    result = runner.invoke(
        cli_main.app, 
        ["works", "--oa-status", "bronze:hybrid"]
    )
    assert result.exit_code == 0
    # bronze(1) to hybrid(2) -> [bronze, hybrid]
    assert recorded_kwargs["oa_status"] == "bronze|hybrid"
