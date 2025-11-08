"""Tests for the technology landscaping agents."""

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.fake import FakeListLLM

from pyalex.agents import LandscapeAgentConfig
from pyalex.agents import TechnologyLandscaper
from pyalex.agents.landscaping import LandscapeReport
from pyalex.agents.landscaping import analyze_jsonl_file


class _StaticEmbeddingModel(Embeddings):
    """Simple embedding mock that returns deterministic vectors."""

    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self._mapping = mapping

    def embed_documents(self, texts: list[str]) -> list[list[float]]:  # type: ignore[override]
        return [self._mapping.get(text, [0.0, 0.0]) for text in texts]

    def embed_query(self, text: str) -> list[float]:  # type: ignore[override]
        return self._mapping.get(text, [0.0, 0.0])


@pytest.fixture()
def fake_landscaper() -> TechnologyLandscaper:
    responses = [
        "Objective summary",
        "- Outcome 1",
        "Key methods",
        "Concept: early research",
        "Strategic insight",
    ]
    llm = FakeListLLM(responses=responses)
    return TechnologyLandscaper(llm, config=LandscapeAgentConfig(trace=True))


def test_analyze_entry(fake_landscaper: TechnologyLandscaper) -> None:
    entry = {
        "id": "W1",
        "title": "Test Work",
        "title_abstract": "Title: Test Work\nAbstract: Details",
    }
    report = fake_landscaper.analyze_entry(entry)

    assert isinstance(report, LandscapeReport)
    assert report.entry_id == "W1"
    assert report.objective == "Objective summary"
    assert "Outcome" in report.outcomes
    assert report.metadata["title"] == "Test Work"
    assert report.embedding is None
    assert report.component_embeddings is None


def test_analyze_entry_with_embeddings() -> None:
    responses = [
        "Objective summary",
        "- Outcome 1",
        "Key methods",
        "Concept: early research",
        "Strategic insight",
    ]
    llm = FakeListLLM(responses=responses)
    embedding_model = _StaticEmbeddingModel(
        {
            "Title: Test Work\nAbstract: Details": [6.0, 0.0],
            "Objective summary": [0.0, 1.0],
            "- Outcome 1": [0.0, 2.0],
            "Key methods": [0.0, 3.0],
            "Concept: early research": [0.0, 4.0],
            "Strategic insight": [0.0, 5.0],
        }
    )
    landscaper = TechnologyLandscaper(llm, embedding_model=embedding_model)

    entry = {
        "id": "W1",
        "title": "Test Work",
        "title_abstract": "Title: Test Work\nAbstract: Details",
    }

    report = landscaper.analyze_entry(entry)

    assert report.embedding == pytest.approx([1.0, 2.5])
    assert report.component_embeddings is not None
    assert set(report.component_embeddings) == {
        "text",
        "objective",
        "outcomes",
        "methods",
        "readiness",
        "insight",
    }
    assert report.component_embeddings["text"] == [6.0, 0.0]


def test_analyze_entries_from_jsonl(
    tmp_path: Path, fake_landscaper: TechnologyLandscaper
) -> None:
    jsonl_path = tmp_path / "sample.jsonl"
    jsonl_path.write_text(
        '{"id": "W1", "title": "Sample", "title_abstract": "Title: Sample"}\n',
        encoding="utf-8",
    )

    reports = analyze_jsonl_file(jsonl_path, fake_landscaper)
    assert len(reports) == 1
    assert reports[0].title == "Sample"


def test_compute_semantic_shift(fake_landscaper: TechnologyLandscaper) -> None:
    embedding_model = _StaticEmbeddingModel(
        {
            "Title: Test Work\nAbstract: Details": [1.0, 0.0],
            "Title: New Work\nAbstract: Updated": [0.0, 1.0],
        }
    )
    landscaper = TechnologyLandscaper(
        FakeListLLM(
            responses=["Objective", "- Outcome", "Method", "Concept", "Insight"]
        ),
        embedding_model=embedding_model,
    )

    baseline = [
        LandscapeReport(
            entry_id="W1",
            title="Old",
            objective="Objective",
            outcomes="Outcome",
            methods="Method",
            readiness="Concept",
            insight="Insight",
            embedding=[1.0, 0.0],
        )
    ]
    comparison_reports = [
        LandscapeReport(
            entry_id="W2",
            title="New",
            objective="New Objective",
            outcomes="New Outcome",
            methods="New Method",
            readiness="Deployment",
            insight="Insight",
            embedding=[0.0, 1.0],
        )
    ]

    shift = landscaper.compute_semantic_shift(
        baseline,
        comparison_reports,
        baseline_label="2024",
        comparison_label="2025",
    )

    assert shift.centroid_similarity < 0.5
    assert shift.representative_new_entries[0].entry_id == "W2"
    assert shift.summary is not None