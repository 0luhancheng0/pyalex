# Datasets for Collaboration Prediction Experiment

Three pre-configured datasets, each representing two research communities.
Each directory contains a `Makefile` that fetches data, builds the graph,
and runs the experiment.

---

## Dataset 1: `quantum_vs_rl/`
**Quantum computing** vs **Reinforcement learning** — topically disjoint
communities seeded from keyword searches. Both are active, high-output fields
with clear separation in content space.

## Dataset 2: `mit_cs_vs_cambridge_cs/`
**MIT CSAIL** (I136199984) vs **Cambridge CS** (I33216779) — two top CS
departments. Institutional seeding captures real community structure.
Cross-institution collaborations provide the interesting positive signal.

## Dataset 3: `computational_biology_vs_nlp/`
**Computational biology** vs **NLP** — two fields that have significant
potential for cross-disciplinary collaboration (e.g. bioinformatics + LLMs)
making this a harder, more realistic dataset.

---

## Common Pipeline

```
works_a.jsonl + works_b.jsonl
      ↓ (pyalex network build --edge-type authorship)
network.graphml
      ↓ (collaboration_prediction.py prepare)
results.json
      ↓ (collaboration_prediction.py evaluate)
printed comparison table
```

## Running All Datasets

```bash
cd pyalex/embeddings/experiments/datasets
make -C quantum_vs_rl/
make -C mit_cs_vs_cambridge_cs/
make -C computational_biology_vs_nlp/
```
