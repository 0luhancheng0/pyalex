# Create tests/test_expand_year.py
import json
import subprocess
import os

def test_expand_author_work_year_filter():
    # Use a known author ID and year range
    # Note: Requires network or mock. Assuming environment supports live tests or mocks are in place.
    # For a robust plan, we use a small input file.
    with open("temp_authors.jsonl", "w") as f:
        f.write(json.dumps({"id": "https://openalex.org/A5023888391"}) + "\n")
    
    try:
        cmd = [
            "python", "-m", "pyalex", "expand", 
            "--mode", "author_work", 
            "-i", "temp_authors.jsonl", 
            "--year", "2017:2018",
            "--jsonl"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split("\n")
        assert len(lines) > 0
        for line in lines:
            if not line.strip(): continue
            data = json.loads(line)
            year = data.get("publication_year")
            assert 2017 <= year <= 2018
    finally:
        if os.path.exists("temp_authors.jsonl"):
            os.remove("temp_authors.jsonl")

def test_expand_work_related_year_filter():
    with open("temp_works.jsonl", "w") as f:
        f.write(json.dumps({"id": "https://openalex.org/W2741809807"}) + "\n")
    
    try:
        cmd = [
            "python", "-m", "pyalex", "expand", 
            "--mode", "work_related", 
            "-i", "temp_works.jsonl", 
            "--year", "2020",
            "--jsonl"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split("\n")
        if lines and lines[0]:
            for line in lines:
                data = json.loads(line)
                assert data.get("publication_year") == 2020
    finally:
        if os.path.exists("temp_works.jsonl"):
            os.remove("temp_works.jsonl")
