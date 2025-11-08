"""FastMCP server exposing PyAlex functionality to LLM agents."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from collections.abc import Mapping
from typing import Any

from fastmcp.server import Context
from fastmcp.server import FastMCP

from pyalex import Authors
from pyalex import Works

server = FastMCP(
    name="pyalex",
    instructions=(
        "Use these tools to search the OpenAlex corpus. Provide concise queries and "
        "keep `limit` requests modest to avoid rate limits."
    ),
)


def _normalize_iterable(values: Iterable[Any]) -> list[Any]:
    return [_normalize_value(value) for value in values]


def _normalize_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _normalize_value(value) for key, value in data.items()}


def _normalize_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _normalize_mapping(value)
    if isinstance(value, (list, tuple, set)):
        return _normalize_iterable(value)
    return str(value)


def _select_fields_from_string(select: str | None) -> list[str] | None:
    if not select:
        return None
    fields = [part.strip() for part in select.split(",") if part.strip()]
    return fields or None


def _apply_common_query_options(
    entity: Any,
    *,
    search: str | None,
    filters: Mapping[str, Any] | None,
    select: list[str] | None,
    sort: str | None,
) -> Any:
    if search:
        entity = entity.search(search)

    if filters:
        for filter_key, filter_value in filters.items():
            entity = entity.filter(**{filter_key: filter_value})

    if select:
        entity = entity.select(select)

    if sort:
        sort_params: dict[str, str] = {}
        for item in sort.split(","):
            piece = item.strip()
            if not piece:
                continue
            if ":" in piece:
                field, direction = piece.split(":", 1)
                sort_params[field.strip()] = direction.strip()
            else:
                sort_params[piece] = "asc"
        if sort_params:
            entity = entity.sort(**sort_params)

    return entity


def _execute_query(
    entity_cls: Any,
    *,
    search: str | None,
    limit: int,
    select: list[str] | None,
    filters: Mapping[str, Any] | None,
    sort: str | None,
) -> dict[str, Any]:
    entity = entity_cls()
    entity = _apply_common_query_options(
        entity,
        search=search,
        filters=filters,
        select=select,
        sort=sort,
    )

    results = entity[:limit]

    if hasattr(results, "to_dict"):
        records = results.to_dict("records")  # type: ignore[assignment]
    else:
        records = list(results)

    normalized = [_normalize_mapping(dict(record)) for record in records]
    return {
        "results": normalized,
        "count": len(normalized),
    }


def _ensure_mapping(
    value: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("filters must be a mapping of field names to values")
    return value


@server.tool(name="search_works", description="Search OpenAlex works via PyAlex")
async def search_works(  # pragma: no cover - integration exercise
    context: Context,
    query: str | None = None,
    limit: int = 25,
    select: str | None = None,
    filters: Mapping[str, Any] | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    """Search OpenAlex works."""

    del context  # Context currently unused but available for future features

    limit = max(1, min(limit, 100))
    select_fields = _select_fields_from_string(select)

    validated_filters = _ensure_mapping(filters)

    result = await asyncio.to_thread(
        _execute_query,
        Works,
        search=query,
        limit=limit,
        select=select_fields,
        filters=validated_filters,
        sort=sort,
    )

    return {
        "entity": "works",
        "meta": {"limit": limit, "query": query, "select": select_fields},
        **result,
    }


@server.tool(name="search_authors", description="Search OpenAlex authors via PyAlex")
async def search_authors(  # pragma: no cover - integration exercise
    context: Context,
    query: str | None = None,
    limit: int = 25,
    select: str | None = None,
    filters: Mapping[str, Any] | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    """Search OpenAlex authors."""

    del context

    limit = max(1, min(limit, 100))
    select_fields = _select_fields_from_string(select)

    validated_filters = _ensure_mapping(filters)

    result = await asyncio.to_thread(
        _execute_query,
        Authors,
        search=query,
        limit=limit,
        select=select_fields,
        filters=validated_filters,
        sort=sort,
    )

    return {
        "entity": "authors",
        "meta": {"limit": limit, "query": query, "select": select_fields},
        **result,
    }


def main() -> None:
    """Run the PyAlex MCP server using stdio transport by default."""

    server.run(transport='http')


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
