# Fix Trajectory Makefile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the trajectory generation in the trajectories example by ensuring all required axis topics are preserved in the network graph, even if they have no connected works.

**Architecture:** Add the `--no-prune` flag to the `pyalex network build` command in the Makefile. This prevents the automatic removal of isolated topic nodes which are required for ternary projection axes.

**Tech Stack:** Makefile, pyalex CLI

---

### Task 1: Update Makefile

**Files:**
- Modify: `experiments/datasets/trajectories/Makefile`

- [ ] **Step 1: Add --no-prune to network.graphml target**

Update the `network.graphml` target to include `--no-prune`.

```makefile
# 4. Build the network
network.graphml: works.jsonl topics.jsonl
	$(PYALEX) network build \
	    -i works.jsonl \
	    -i topics.jsonl \
	    -o $@ \
	    --edge-type authorship \
	    --edge-type topic \
	    --no-prune
```

- [ ] **Step 2: Commit changes**

```bash
git add experiments/datasets/trajectories/Makefile
git commit -m "fix: add --no-prune to trajectory network build to preserve axis topics"
```

### Task 2: Verification (Manual)

- [ ] **Step 1: Run the Makefile**

Run `make clean && make` in the `experiments/datasets/trajectories` directory.

Run: `cd experiments/datasets/trajectories && make clean && make`
Expected: Successful completion without "Topic T10002 not found" error, and generation of `trajectory.png`.
