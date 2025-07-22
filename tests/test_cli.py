#!/usr/bin/env python3
"""
Tests for PyAlex CLI
"""
import subprocess
import json
import pytest


def test_cli_help():
    """Test that the CLI help command works."""
    result = subprocess.run(
        ["pyalex", "--help"], 
        capture_output=True, 
        text=True
    )
    assert result.returncode == 0
    assert "CLI interface for the OpenAlex database" in result.stdout


def test_works_help():
    """Test that the works subcommand help works."""
    result = subprocess.run(
        ["pyalex", "works", "--help"], 
        capture_output=True, 
        text=True
    )
    assert result.returncode == 0
    assert "Search and retrieve works from OpenAlex" in result.stdout


def test_authors_help():
    """Test that the authors subcommand help works."""
    result = subprocess.run(
        ["pyalex", "authors", "--help"], 
        capture_output=True, 
        text=True
    )
    assert result.returncode == 0
    assert "Search and retrieve authors from OpenAlex" in result.stdout


def test_topics_help():
    """Test that the topics subcommand help works."""
    result = subprocess.run(
        ["pyalex", "topics", "--help"], 
        capture_output=True, 
        text=True
    )
    assert result.returncode == 0
    assert "Search and retrieve topics from OpenAlex" in result.stdout


def test_works_search():
    """Test that works search returns results."""
    result = subprocess.run(
        ["pyalex", "works", "--search", "test", "--limit", "1", "--format", "json"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    
    # Check that we get valid JSON
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) <= 1  # Should be at most 1 result due to limit


def test_works_summary_format():
    """Test that works search returns summary format by default."""
    result = subprocess.run(
        ["pyalex", "works", "--search", "test", "--limit", "1"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "[1]" in result.stdout  # Should show numbered results
    assert "Title:" in result.stdout
    assert "ID:" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__])
