"""Technology landscaping agents powered by LangChain."""

import json
import math
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig, RunnableParallel


OBJECTIVE_PROMPT = ChatPromptTemplate.from_template(
    "You are a research analyst. Summarise the primary research objective described "
    "in the provided title and abstract. Focus on the problem the work addresses and "
    "the intended contribution. Keep the answer under 80 words.\n\n"
    "Title: {title}\n"
    "Text: {text}\n"
)

OUTCOME_PROMPT = ChatPromptTemplate.from_template(
    "You extract the main outcomes or findings for technology landscaping. List the "
    "key results, validations, or conclusions the work reports in bullet form. Keep "
    "bullets concise (under 20 words) and return a single markdown string.\n\n"
    "Title: {title}\n"
    "Text: {text}\n"
)

METHOD_PROMPT = ChatPromptTemplate.from_template(
    "Identify the principal approaches, datasets, architectures, or techniques used in "
    "this work. Be specific about what makes the method notable. Respond in three "
    "short sentences or fewer.\n\n"
    "Title: {title}\n"
    "Text: {text}\n"
)

READINESS_PROMPT = ChatPromptTemplate.from_template(
    "Assess the maturity and readiness of the described technology. Classify it into "
    "one of the following buckets: concept, laboratory validation, pilot deployment, "
    "production-ready. Justify the classification in one sentence.\n\n"
    "Title: {title}\n"
    "Text: {text}\n"
)

INSIGHT_PROMPT = ChatPromptTemplate.from_template(
    "Provide a strategic takeaway that a product leader should know about this work. "
    "Highlight differentiation, potential impact, or open risks in at most three "
    "sentences.\n\n"
    "Objective: {objective}\n"
    "Outcomes: {outcomes}\n"
    "Methods: {methods}\n"
    "Readiness: {readiness}\n"
)

SHIFT_SUMMARY_PROMPT = ChatPromptTemplate.from_template(
    "You compare two yearly research corpora. Using the provided metrics, explain "
    "notable shifts between {baseline_label} and {comparison_label} in six sentences "
    "or fewer. Emphasise emerging topics, declining themes, or changes in maturity.\n\n"
    "Centroid similarity: {centroid_similarity:.3f}\n"
    "{baseline_label} dispersion: {baseline_dispersion:.3f}\n"
    "{comparison_label} dispersion: {comparison_dispersion:.3f}\n\n"
    "Representative {baseline_label} objectives:\n"
    "{baseline_examples}\n\n"
    "Representative {comparison_label} objectives:\n"
    "{comparison_examples}\n"
)
@dataclass(slots=True)
class LandscapeReport:
    """Structured summary for a single research artefact."""

    entry_id: str
    title: str
    objective: str
    outcomes: str
    methods: str
    readiness: str
    insight: str
    embedding: list[float] | None = None
    component_embeddings: dict[str, list[float]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""

        return {
            "entry_id": self.entry_id,
            "title": self.title,
            "objective": self.objective,
            "outcomes": self.outcomes,
            "methods": self.methods,
            "readiness": self.readiness,
            "insight": self.insight,
            "embedding": self.embedding,
            "component_embeddings": self.component_embeddings,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class SemanticShiftReport:
    """Encapsulates shift metrics computed from embeddings."""

    baseline_label: str
    comparison_label: str
    centroid_similarity: float
    baseline_dispersion: float
    comparison_dispersion: float
    representative_new_entries: list[LandscapeReport]
    summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""

        return {
            "baseline_label": self.baseline_label,
            "comparison_label": self.comparison_label,
            "centroid_similarity": self.centroid_similarity,
            "baseline_dispersion": self.baseline_dispersion,
            "comparison_dispersion": self.comparison_dispersion,
            "representative_new_entries": [
                entry.to_dict()
                for entry in self.representative_new_entries
            ],
            "summary": self.summary,
        }


@dataclass(slots=True)
class LandscapeAgentConfig:
    """Configuration for the technology landscaping workflow."""

    text_field: str = "title_abstract"
    metadata_fields: Sequence[str] = ()
    trace: bool = False
    max_trace_items: int = 10


class TechnologyLandscaper:
    """Coordinates LangChain-powered agents for research landscaping."""

    def __init__(
        self,
        llm: Runnable,
        *,
        embedding_model: Embeddings | None = None,
        config: LandscapeAgentConfig | None = None,
    ) -> None:
        self._llm = llm
        self._embedding_model = embedding_model
        self._config = config or LandscapeAgentConfig()
        self._objective_chain = OBJECTIVE_PROMPT | self._llm | StrOutputParser()
        self._outcome_chain = OUTCOME_PROMPT | self._llm | StrOutputParser()
        self._method_chain = METHOD_PROMPT | self._llm | StrOutputParser()
        self._readiness_chain = READINESS_PROMPT | self._llm | StrOutputParser()
        self._insight_chain = INSIGHT_PROMPT | self._llm | StrOutputParser()
        self._parallel_agents = RunnableParallel(
            objective=self._objective_chain,
            outcomes=self._outcome_chain,
            methods=self._method_chain,
            readiness=self._readiness_chain,
        )

    def analyze_entries(
        self,
        entries: Iterable[Mapping[str, Any]],
        *,
        config: RunnableConfig | None = None,
    ) -> list[LandscapeReport]:
        return [self.analyze_entry(entry, config=config) for entry in entries]

    def analyze_entry(
        self,
        entry: Mapping[str, Any],
        *,
        config: RunnableConfig | None = None,
    ) -> LandscapeReport:
        text_field = self._config.text_field
        if text_field not in entry or not entry[text_field]:
            raise ValueError(f"Entry missing required text field '{text_field}'")

        text_value = str(entry[text_field])
        title = str(entry.get("title", ""))
        entry_id = str(entry.get("id", ""))

        base_inputs = {"title": title, "text": text_value}
        parallel_results = self._parallel_agents.invoke(base_inputs, config=config)

        objective = parallel_results.get("objective", "").strip()
        outcomes = parallel_results.get("outcomes", "").strip()
        methods = parallel_results.get("methods", "").strip()
        readiness = parallel_results.get("readiness", "").strip()

        insight = self._insight_chain.invoke(
            {
                "objective": objective,
                "outcomes": outcomes,
                "methods": methods,
                "readiness": readiness,
            },
            config=config,
        ).strip()

        metadata = self._collect_metadata(entry)

        component_embeddings: dict[str, list[float]] | None = None
        embedding: list[float] | None = None
        if self._embedding_model is not None:
            # Embed source text together with agent outputs for downstream analysis.
            component_texts = [
                ("text", text_value),
                ("objective", objective),
                ("outcomes", outcomes),
                ("methods", methods),
                ("readiness", readiness),
                ("insight", insight),
            ]
            non_empty_components = [
                (name, value) for name, value in component_texts if value
            ]
            if non_empty_components:
                vectors = self._embedding_model.embed_documents(
                    [value for _, value in non_empty_components]
                )
                component_embeddings = {}
                for (name, _), vector in zip(
                    non_empty_components,
                    vectors,
                    strict=True,
                ):
                    component_embeddings[name] = list(vector)
                embedding = _mean_vector(list(component_embeddings.values()))

        if self._config.trace:
            trace: list[dict[str, str]] = []
            for agent_name, content in (
                ("objective_agent", objective),
                ("outcome_agent", outcomes),
                ("method_agent", methods),
                ("readiness_agent", readiness),
                ("insight_agent", insight),
            ):
                if not content:
                    continue
                trace.append({"agent": agent_name, "content": content})
                if len(trace) >= self._config.max_trace_items:
                    break
            if trace:
                metadata = dict(metadata)
                metadata["trace"] = trace

        return LandscapeReport(
            entry_id=entry_id,
            title=title,
            objective=objective,
            outcomes=outcomes,
            methods=methods,
            readiness=readiness,
            insight=insight,
            embedding=embedding,
            component_embeddings=component_embeddings,
            metadata=metadata,
        )

    def compute_semantic_shift(
        self,
        baseline_reports: Sequence[LandscapeReport],
        comparison_reports: Sequence[LandscapeReport],
        *,
        baseline_label: str,
        comparison_label: str,
        summary_llm: Runnable | None = None,
        top_k: int = 3,
    ) -> SemanticShiftReport:
        if self._embedding_model is None:
            raise ValueError("Embedding model required to compute semantic shift")

        baseline_vectors = [
            report.embedding
            for report in baseline_reports
            if report.embedding is not None
        ]
        comparison_vectors = [
            report.embedding
            for report in comparison_reports
            if report.embedding is not None
        ]
        if not baseline_vectors or not comparison_vectors:
            raise ValueError("Both corpora need embeddings to compute semantic shift")

        baseline_centroid = _mean_vector(baseline_vectors)
        comparison_centroid = _mean_vector(comparison_vectors)

        centroid_similarity = _cosine_similarity(baseline_centroid, comparison_centroid)
        baseline_dispersion = _mean_distance_to_centroid(
            baseline_vectors,
            baseline_centroid,
        )
        comparison_dispersion = _mean_distance_to_centroid(
            comparison_vectors,
            comparison_centroid,
        )

        ranked_new_entries = _rank_by_similarity(
            comparison_reports,
            baseline_centroid,
        )
        representative_new = ranked_new_entries[: top_k or 3]

        summary_text: str | None = None
        llm_for_summary = summary_llm or self._llm
        if llm_for_summary is not None:
            summary_examples = (
                SHIFT_SUMMARY_PROMPT
                | llm_for_summary
                | StrOutputParser()
            )
            baseline_examples = _truncate_examples(
                baseline_reports,
                key="objective",
            )
            comparison_examples = _truncate_examples(
                representative_new,
                key="objective",
            )
            summary_text = summary_examples.invoke(
                {
                    "baseline_label": baseline_label,
                    "comparison_label": comparison_label,
                    "centroid_similarity": centroid_similarity,
                    "baseline_dispersion": baseline_dispersion,
                    "comparison_dispersion": comparison_dispersion,
                    "baseline_examples": baseline_examples,
                    "comparison_examples": comparison_examples,
                }
            )

        return SemanticShiftReport(
            baseline_label=baseline_label,
            comparison_label=comparison_label,
            centroid_similarity=centroid_similarity,
            baseline_dispersion=baseline_dispersion,
            comparison_dispersion=comparison_dispersion,
            representative_new_entries=representative_new,
            summary=summary_text,
        )

    def _collect_metadata(self, entry: Mapping[str, Any]) -> dict[str, Any]:
        if not self._config.metadata_fields:
            return {k: v for k, v in entry.items() if k != self._config.text_field}
        return {field: entry.get(field) for field in self._config.metadata_fields}


def analyze_jsonl_file(
    path: str | Path,
    landscaper: TechnologyLandscaper,
    *,
    config: RunnableConfig | None = None,
) -> list[LandscapeReport]:
    """Load a JSONL file and generate reports for each entry."""

    entries = list(load_jsonl(path))
    return landscaper.analyze_entries(entries, config=config)


def load_jsonl(path: str | Path) -> Iterable[MutableMapping[str, Any]]:
    """Yield entries from a newline-delimited JSON file."""

    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Could not find JSONL file at {resolved}")

    with resolved.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                entry = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {resolved}"
                ) from exc
            if not isinstance(entry, MutableMapping):
                raise ValueError(
                    "Expected JSON object on line "
                    f"{line_number} of {resolved}, got {type(entry)!r}"
                )
            yield entry


def _mean_vector(vectors: Sequence[Sequence[float]]) -> list[float]:
    if not vectors:
        raise ValueError("Cannot compute mean of empty vectors")
    length = len(vectors[0])
    totals = [0.0] * length
    for vector in vectors:
        if len(vector) != length:
            raise ValueError("Vectors must be of equal length")
        for index, value in enumerate(vector):
            totals[index] += value
    count = float(len(vectors))
    return [total / count for total in totals]


def _cosine_similarity(lhs: Sequence[float], rhs: Sequence[float]) -> float:
    if len(lhs) != len(rhs):
        raise ValueError("Vectors must be of equal length for cosine similarity")
    dot = 0.0
    lhs_norm = 0.0
    rhs_norm = 0.0
    for a, b in zip(lhs, rhs, strict=True):
        dot += a * b
        lhs_norm += a * a
        rhs_norm += b * b
    if lhs_norm == 0 or rhs_norm == 0:
        return 0.0
    return dot / (math.sqrt(lhs_norm) * math.sqrt(rhs_norm))


def _mean_distance_to_centroid(
    vectors: Sequence[Sequence[float]],
    centroid: Sequence[float],
) -> float:
    if not vectors:
        return 0.0
    total = 0.0
    for vector in vectors:
        similarity = _cosine_similarity(vector, centroid)
        total += 1 - similarity
    return total / float(len(vectors))


def _rank_by_similarity(
    reports: Sequence[LandscapeReport],
    centroid: Sequence[float],
) -> list[LandscapeReport]:
    scored: list[tuple[float, LandscapeReport]] = []
    for report in reports:
        if not report.embedding:
            continue
        similarity = _cosine_similarity(report.embedding, centroid)
        scored.append((similarity, report))
    scored.sort(key=lambda item: item[0])
    return [report for _, report in scored]


def _truncate_examples(
    reports: Sequence[LandscapeReport],
    *,
    key: str,
    limit: int = 3,
) -> str:
    collected: list[str] = []
    for report in reports:
        value = getattr(report, key, "")
        if value:
            collected.append(value)
        if len(collected) >= limit:
            break
    if not collected:
        return "(no examples)"
    return "\n".join(f"- {snippet}" for snippet in collected)

# from langchain_openai import ChatOpenAI 
# llm = ChatOpenAI(model="gpt-5-mini")

# analyser = TechnologyLandscaper(llm)
# analyser._parallel_agents