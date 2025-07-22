#!/usr/bin/env python3
"""
Example CLI usage for PyAlex

This script demonstrates how to use the PyAlex CLI for various queries.
Run this script to see example outputs.
"""

import subprocess


def run_cli_command(command):
    """Run a CLI command and return the result."""
    print(f"\n🔍 Running: {' '.join(command)}")
    print("=" * 50)
    
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"Error: {result.stderr}")
    
    return result


def main():
    """Demonstrate CLI functionality."""
    print("PyAlex CLI Demo")
    print("===============")
    
    # Test 1: Search for works about machine learning
    run_cli_command([
        "pyalex", "works", 
        "--search", "machine learning", 
        "--limit", "3"
    ])
    
    # Test 2: Search for authors
    run_cli_command([
        "pyalex", "authors", 
        "--search", "Einstein", 
        "--limit", "2"
    ])
    
    # Test 3: Search for topics  
    run_cli_command([
        "pyalex", "topics", 
        "--search", "climate change", 
        "--limit", "2"
    ])
    
    # Test 4: Get works in title format
    run_cli_command([
        "pyalex", "works", 
        "--search", "quantum computing", 
        "--limit", "3",
        "--format", "title"
    ])
    
    # Test 5: Get a specific work by ID (JSON format)
    run_cli_command([
        "pyalex", "works", "W2741809807", 
        "--format", "json"
    ])
    
    print("\n✅ Demo completed successfully!")
    print("\nTry running these commands yourself:")
    print("  pyalex --help")
    print("  pyalex works --help")
    print("  pyalex works --search 'your topic' --limit 5")
    print("  pyalex authors --search 'author name'")
    print("  pyalex topics --search 'field of study'")


if __name__ == "__main__":
    main()
