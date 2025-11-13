from __future__ import annotations

import operator
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
    
from itertools import count

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


# llm = ChatOpenAI(model="gpt-5-mini")
llm = ChatOpenAI(model="Qwen/Qwen3-4B-Instruct-2507", base_url="http://localhost:8000/v1")

taxonomy_agent_system_prompt = dedent(
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


taxonomy_agent = create_agent(
    model=llm,
    system_prompt=taxonomy_agent_system_prompt,
    response_format=ProviderStrategy(Taxonomy),
)


taxonomy_merge_agent_system_prompt = dedent(
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


taxonomy_merge_agent = create_agent(
    model=llm,
    system_prompt=taxonomy_merge_agent_system_prompt,
    response_format=ProviderStrategy(Taxonomy),
)


def generate_taxonomy(state: State, config: RunnableConfig | None = None) -> dict:
    """Run the taxonomy agent across works converted into batched messages."""

    default_batch_size = 20
    batch_size = default_batch_size
    if config and "metadata" in config:
        batch_size = config["metadata"].get("batch_size", default_batch_size)

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

    taxonomy_list = taxonomy_agent.batch(messages)
    structured_responses = [
        response["structured_response"]
        for response in taxonomy_list
        if "structured_response" in response
    ]
    return {"taxonomy_list": structured_responses}


def merge_taxonomies(state: State) -> dict:
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
    response = taxonomy_merge_agent.batch([prompt_value])[0]
    return {"merged_taxonomy": response.get("structured_response")}


graph_builder = StateGraph(State)
graph_builder.add_node("generate_taxonomy", generate_taxonomy)
graph_builder.add_node("merge_taxonomies", merge_taxonomies)
graph_builder.add_edge(START, "generate_taxonomy")
graph_builder.add_edge("generate_taxonomy", "merge_taxonomies")
graph_builder.add_edge("merge_taxonomies", END)
graph = graph_builder.compile()


DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "2025.jsonl"


def load_works(data_path: Path = DEFAULT_DATA_PATH) -> list[dict]:
    """Load works data from a JSONL file."""

    return pd.read_json(data_path, lines=True).to_dict(orient="records")


def run_taxonomy_pipeline(
    works: list[dict],
    batch_size: int = 20,
) -> Taxonomy | None:
    """Execute the taxonomy graph and return the merged taxonomy."""

    state = graph.invoke(
        {
            "works": works,
            "taxonomy_list": [],
            "merged_taxonomy": None,
        },
        config={"metadata": {"batch_size": batch_size}},
    )
    return state

works = load_works()
state = run_taxonomy_pipeline(works)



