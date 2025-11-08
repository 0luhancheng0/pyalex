"""Tests for the PyAlex MCP server helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import pytest

from pyalex.mcp import server as mcp_server


class DummyEntity:
    """Simple stand-in for PyAlex entity classes used in tests."""

    last_created: DummyEntity | None = None

    def __init__(self) -> None:
        self.__class__.last_created = self
        self.search_term: str | None = None
        self.filters: list[Mapping[str, Any]] = []
        self.selected: list[str] | None = None
        self.sort_args: dict[str, str] | None = None
        self.limit: int | None = None

    def search(self, term: str) -> DummyEntity:
        self.search_term = term
        return self

    def filter(self, **kwargs: Any) -> DummyEntity:
        self.filters.append(kwargs)
        return self

    def select(self, fields: list[str]) -> DummyEntity:
        self.selected = list(fields)
        return self

    def sort(self, **kwargs: str) -> DummyEntity:
        self.sort_args = dict(kwargs)
        return self

    def __getitem__(self, key: slice | int) -> list[dict[str, Any]]:
        if isinstance(key, slice):
            self.limit = key.stop
        else:
            self.limit = key
        return [{"id": "X", "display_name": "Example"}]


def test_execute_query_applies_shared_options() -> None:
    result = mcp_server._execute_query(  # noqa: SLF001
        DummyEntity,
        search="ai",
        limit=5,
        select=["display_name"],
        filters={"works_count": ">100"},
        sort="display_name:desc,popularity",
    )

    entity = DummyEntity.last_created
    assert entity is not None
    assert entity.search_term == "ai"
    assert entity.selected == ["display_name"]
    assert entity.filters == [{"works_count": ">100"}]
    assert entity.limit == 5
    assert entity.sort_args == {"display_name": "desc", "popularity": "asc"}

    assert result == {
        "results": [{"id": "X", "display_name": "Example"}],
        "count": 1,
    }


def test_select_fields_from_string() -> None:
    assert mcp_server._select_fields_from_string("display_name, doi") == [
        "display_name",
        "doi",
    ]
    assert mcp_server._select_fields_from_string("  ") is None


def test_ensure_mapping_validation() -> None:
    filters = {"works_count": ">100"}
    assert mcp_server._ensure_mapping(filters) is filters  # noqa: SLF001

    with pytest.raises(ValueError):
        mcp_server._ensure_mapping([("a", 1)])  # type: ignore[arg-type]  # noqa: SLF001


@pytest.mark.asyncio
async def test_search_works_caps_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_to_thread(func, *args, **kwargs):  # type: ignore[no-untyped-def]
        return func(*args, **kwargs)

    calls: dict[str, Any] = {}

    def fake_execute_query(entity_cls, **kwargs):  # type: ignore[no-untyped-def]
        calls["entity_cls"] = entity_cls
        calls["kwargs"] = kwargs
        return {"results": [{"id": "W1"}], "count": 1}

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(mcp_server, "_execute_query", fake_execute_query)

    response = await mcp_server.search_works(  # noqa: SLF001
        context=None,  # type: ignore[arg-type]
        query="climate",
        limit=500,
        select="display_name,doi",
        filters={"works_count": ">100"},
        sort="display_name:desc",
    )

    assert response["entity"] == "works"
    assert response["meta"] == {
        "limit": 100,
        "query": "climate",
        "select": ["display_name", "doi"],
    }
    assert response["results"] == [{"id": "W1"}]

    assert calls["entity_cls"] is mcp_server.Works
    assert calls["kwargs"] == {
        "search": "climate",
        "limit": 100,
        "select": ["display_name", "doi"],
        "filters": {"works_count": ">100"},
        "sort": "display_name:desc",
    }


@pytest.mark.asyncio
async def test_search_authors_honours_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_to_thread(func, *args, **kwargs):  # type: ignore[no-untyped-def]
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    def fake_execute_query(entity_cls, **kwargs):  # type: ignore[no-untyped-def]
        return {"results": [{"id": "A1"}], "count": 1}

    monkeypatch.setattr(mcp_server, "_execute_query", fake_execute_query)

    response = await mcp_server.search_authors(  # noqa: SLF001
        context=None,  # type: ignore[arg-type]
        query=None,
        limit=0,
        select=None,
        filters=None,
        sort=None,
    )

    assert response["entity"] == "authors"
    assert response["meta"]["limit"] == 1
