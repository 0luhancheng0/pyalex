from __future__ import annotations

import operator
from itertools import count
from pathlib import Path
from textwrap import dedent
from typing import Annotated

import pandas as pd
from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain_core.messages import HumanMessage
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.runnables.config import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from treelib import Tree


class Category(BaseModel):
    name: str = Field(..., description="The name of the category.")
    description: str = Field(..., description="A brief description of the category.")
    subcategories: list[Category] = Field(
        default_factory=list,
        description=(
            "A list of subcategories. Empty if the current category is a leaf node."
        ),
    )


class Taxonomy(BaseModel):
    category_list: list[Category] = Field(
        ...,
        description="A list of taxonomy items in nested bullet point format.",
    )


class State(BaseModel):
    works: Annotated[list[dict], operator.add] = Field(
        ..., description="A list of works with title and abstract."
    )
    taxonomy_list: Annotated[list[Taxonomy], operator.add] = Field(
        default_factory=list,
        description="The generated taxonomy from the works.",
    )
    merged_taxonomy: Taxonomy | None = Field(
        default=None,
        description="A single taxonomy merged from the generated batches.",
    )


def taxonomy_to_tree(taxonomy: Taxonomy) -> Tree:
    """Convert a `Taxonomy` into a `treelib` representation."""

    tree = Tree()
    # tree.create_node("Taxonomy", "taxonomy")
    tree.create_node(tag="Taxonomy", identifier="taxonomy", data=None)

    id_counter = count()

    def _add_category(category: Category, parent_id: str) -> None:
        node_id = f"node-{next(id_counter)}"
        tree.create_node(
            tag=category.name,
            identifier=node_id,
            parent=parent_id,
            data={
                "name": category.name,
                "description": category.description,
                "subcategories": category.subcategories,
            },
        )
        for child in category.subcategories:
            _add_category(child, node_id)

    for top_level in taxonomy.category_list:
        _add_category(top_level, "taxonomy")

    return tree


TAXONOMY_AGENT_SYSTEM_PROMPT = dedent(
    f"""
    You are an expert engineer collaborating on a technology landscaping workflow.

    # Objective
    Your task is to create a taxonomy from research documents that consist of title and abstracts.

    # Constraints
    - Your taxonomy should be hierarchical and cover the major topics found in the documents.
    - Skip any topic that does not appear in the source documents.
    - Give each category a name and a brief description.
    - Do NOT include the input documents as taxonomy entries.

    # Output Format
    Here is the model JSON schema describing the output format you should follow:
    {Taxonomy.model_json_schema()}
    """
)


TAXONOMY_MERGE_AGENT_SYSTEM_PROMPT = dedent(
    f"""
    You merge multiple taxonomy batches into a single cohesive hierarchy.

    # Objective
    Combine the provided taxonomy JSON payloads into one taxonomy that captures all relevant topics without duplication.

    # Guidelines
    - Preserve meaningful distinctions between categories; merge overlapping concepts instead of repeating them.
    - Ensure the hierarchy remains balanced and avoids redundant nesting.
    - Keep descriptions concise and grounded in the source category descriptions.

    # Output Format
    Return a single taxonomy following this JSON schema:
    {Taxonomy.model_json_schema()}
    """
)


DEFAULT_MODEL = "Qwen/Qwen3-4B-Instruct-2507"
DEFAULT_BASE_URL = "http://localhost:8000/v1"
DEFAULT_BATCH_SIZE = 20
DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "2025.jsonl"


class TaxonomyPipeline:
    """High-level orchestration for generating and merging taxonomies."""

    def __init__(
        self,
        llm: ChatOpenAI | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.llm = llm or ChatOpenAI(model=DEFAULT_MODEL, base_url=DEFAULT_BASE_URL)
        self.batch_size = batch_size
        self.taxonomy_agent = self._create_taxonomy_agent()
        self.merge_agent = self._create_merge_agent()
        self.graph = self._build_graph()

    def _create_taxonomy_agent(self):
        return create_agent(
            model=self.llm,
            system_prompt=TAXONOMY_AGENT_SYSTEM_PROMPT,
            response_format=ProviderStrategy(Taxonomy),
        )

    def _create_merge_agent(self):
        return create_agent(
            model=self.llm,
            system_prompt=TAXONOMY_MERGE_AGENT_SYSTEM_PROMPT,
            response_format=ProviderStrategy(Taxonomy),
        )

    def _build_graph(self):
        graph_builder = StateGraph(State)
        graph_builder.add_node("generate_taxonomy", self._generate_taxonomy)
        graph_builder.add_node("merge_taxonomies", self._merge_taxonomies)
        graph_builder.add_edge(START, "generate_taxonomy")
        graph_builder.add_edge("generate_taxonomy", "merge_taxonomies")
        graph_builder.add_edge("merge_taxonomies", END)
        return graph_builder.compile()

    def _resolve_batch_size(self, config: RunnableConfig | None) -> int:
        if not config:
            return self.batch_size
        metadata = config.get("metadata") if isinstance(config, dict) else None
        if not metadata:
            return self.batch_size
        return metadata.get("batch_size", self.batch_size)

    def _generate_taxonomy(self, state: State, config: RunnableConfig | None = None) -> dict:
        """Run the taxonomy agent across works converted into batched messages."""

        batch_size = self._resolve_batch_size(config)
        texts = [
            f"Title: {work['title']}\nAbstract: {work['abstract']}"
            for work in state.works
        ]
        batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]
        batch_texts = ["\n\n".join(batch) for batch in batches]
        messages = [
            ChatPromptValue(messages=[HumanMessage(content=batch_text)])
            for batch_text in batch_texts
        ]

        if not messages:
            return {"taxonomy_list": []}

        taxonomy_list = self.taxonomy_agent.batch(messages)
        structured_responses = [
            response.get("structured_response")
            for response in taxonomy_list
            if response.get("structured_response")
        ]
        return {"taxonomy_list": structured_responses}

    def _merge_taxonomies(self, state: State) -> dict:
        """Merge multiple taxonomy batches into a single taxonomy."""

        if not state.taxonomy_list:
            return {"merged_taxonomy": None}

        serialized_batches = [
            f"Taxonomy {index}:\n{taxonomy.model_dump_json(indent=2)}"
            for index, taxonomy in enumerate(state.taxonomy_list, start=1)
        ]
        prompt_value = ChatPromptValue(
            messages=[
                HumanMessage(
                    content="\n\n".join(serialized_batches),
                )
            ]
        )
        response = self.merge_agent.batch([prompt_value])[0]
        return {"merged_taxonomy": response.get("structured_response")}

    def run(
        self,
        works: list[dict],
        *,
        batch_size: int | None = None,
    ) -> Taxonomy | None:
        """Execute the taxonomy graph and return the merged taxonomy."""

        effective_batch_size = batch_size or self.batch_size
        state = self.graph.invoke(
            {
                "works": works,
                "taxonomy_list": [],
                "merged_taxonomy": None,
            },
            config={"metadata": {"batch_size": effective_batch_size}},
        )
        return state


def build_default_pipeline(batch_size: int = DEFAULT_BATCH_SIZE) -> TaxonomyPipeline:
    """Convenience helper to construct a pipeline with default LLM settings."""

    return TaxonomyPipeline(batch_size=batch_size)


def load_works(data_path: Path = DEFAULT_DATA_PATH) -> list[dict]:
    """Load works data from a JSONL file."""

    return pd.read_json(data_path, lines=True).to_dict(orient="records")


def run_taxonomy_pipeline(
    works: list[dict],
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> Taxonomy | None:
    """Execute the taxonomy workflow using default configuration."""

    pipeline = build_default_pipeline(batch_size=batch_size)
    return pipeline.run(works)




if __name__ == "__main__":
    works = load_works()
    pipeline = build_default_pipeline()
    state = pipeline.run(works)
    tree = taxonomy_to_tree(state['merged_taxonomy'])
    tree.show()


