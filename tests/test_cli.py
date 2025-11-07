#!/usr/bin/env python3
"""
Tests for PyAlex CLI
"""

import json
import os
import subprocess
import tempfile

import pytest  # type: ignore[import-not-found]


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
    assert "Display a JSON file containing OpenAlex data" in result.stdout


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
    assert "| title" in header_line
    assert "| fwci" in header_line


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


if __name__ == "__main__":
    pytest.main([__file__])
