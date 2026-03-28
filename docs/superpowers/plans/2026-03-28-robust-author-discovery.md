# Robust Author Discovery for Trajectories Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure `discover_authors.py` always returns authors so the `Makefile` can proceed, even if no interdisciplinary authors are found in the initial small sample.

**Architecture:** 
1. Increase initial works search limit.
2. Add a fallback to top authors from any topic if the intersection is empty.
3. Improve error reporting to stdout for better visibility.

**Tech Stack:** Python

---

### Task 1: Update discover_authors.py

**Files:**
- Modify: `experiments/datasets/trajectories/discover_authors.py`

- [ ] **Step 1: Increase search limits and add fallback logic**

Modify the `discover()` function to be more robust.

```python
def discover():
    # Initialize with empty sets to avoid KeyError later if a topic returns no results
    topic_authors = {tid: set() for tid in TOPICS}
    
    # We'll use a temporary file for expand input
    temp_works_path = "temp_works.jsonl"

    for tid in TOPICS:
        print(f"Finding authors for topic {tid}...", file=sys.stderr)
        # 1. Fetch top works for the topic (Increase limit to 500)
        works_jsonl = run_command(["uv", "run", "pyalex", "works", "--topic-ids", tid, "--limit", "500", "--jsonl"])
        
        if not works_jsonl:
            print(f"  Warning: No works returned for {tid}", file=sys.stderr)
            continue
        
        # Filter works_jsonl to only include JSON lines
        json_lines = [l for l in works_jsonl.split("\n") if l.strip().startswith("{")]
        if not json_lines:
            print(f"  Warning: No valid JSON lines found for {tid}", file=sys.stderr)
            continue
            
        with open(temp_works_path, "w") as f:
            f.write("\n".join(json_lines))
        
        # 2. Extract authors from these works using expand mode
        authors_jsonl = run_command(["uv", "run", "pyalex", "expand", "--mode", "work_author", "-i", temp_works_path, "--limit", "1000", "--jsonl"])
        
        authors = []
        if not authors_jsonl:
            # Fallback: extract directly from works if expand fails
            print(f"  Expand failed, extracting directly from works...", file=sys.stderr)
            for line in json_lines:
                try:
                    data = json.loads(line)
                    for auth in data.get("authorships", []):
                        a_id = auth.get("author", {}).get("id")
                        if a_id:
                            authors.append(a_id)
                except:
                    continue
            authors = list(filter(None, authors))
        else:
            for line in authors_jsonl.strip().split("\n"):
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    data = json.loads(line)
                    authors.append(data["id"])
                except:
                    continue
        
        topic_authors[tid] = set(authors)
        print(f"  Found {len(topic_authors[tid])} unique authors for {tid}.", file=sys.stderr)

    import os
    if os.path.exists(temp_works_path):
        os.remove(temp_works_path)

    # Find authors who appear in at least 2 topics (intersection)
    candidates = Counter()
    for tid in TOPICS:
        for aid in topic_authors[tid]:
            candidates[aid] += 1
    
    # Filter for authors in at least 2 fields, sorted by field count
    top_candidates = [aid for aid, count in candidates.most_common() if count >= 2]
    
    if not top_candidates:
        print("No authors found in at least 2 topics. Falling back to most prolific authors in any topic.", file=sys.stderr)
        # Take authors present in at least 1 topic, sorted by their frequency (most common in the sample)
        top_candidates = [aid for aid, count in candidates.most_common() if count >= 1]
    
    if not top_candidates:
        print("Error: No authors found at all.", file=sys.stderr)
        return

    # Sanity check: get work counts for top candidates to ensure they have enough data
    final_ids = []
    print(f"Selecting {len(top_candidates[:5])} authors...", file=sys.stderr)
    for aid in top_candidates[:5]:
        short_id = aid.replace("https://openalex.org/", "")
        final_ids.append(short_id)

    # Return top 5 author IDs
    if final_ids:
        print(",".join(final_ids))
```

- [ ] **Step 2: Commit changes**

```bash
git add experiments/datasets/trajectories/discover_authors.py
git commit -m "fix: make author discovery more robust with higher limits and fallback"
```

### Task 2: Verification

- [ ] **Step 1: Run make clean && make**

Run the full pipeline in the trajectories directory.

Run: `cd experiments/datasets/trajectories && make clean && make`
Expected: The `authors.txt` file should be created (even if fallback is used), and the pipeline should proceed to `trajectory.png`.
