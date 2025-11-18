from __future__ import annotations

from collections.abc import Callable
from itertools import count
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

import pandas as pd
from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.runnables.config import RunnableConfig
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from langgraph.store.memory import InMemoryStore
from pydantic import BaseModel
from pydantic import Field
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


class TaxonomyEvaluation(BaseModel):
    coverage_score: int = Field(
        ...,
        ge=1,
        le=5,
        description="1 (poor coverage) to 5 (excellent coverage) across the source works.",
    )
    structure_score: int = Field(
        ...,
        ge=1,
        le=5,
        description="1 (disorganized) to 5 (clear hierarchy with balanced depth).",
    )
    description_quality_score: int = Field(
        ...,
        ge=1,
        le=5,
        description="1 (vague descriptions) to 5 (precise, grounded descriptions).",
    )
    strengths: str = Field(
        ...,
        description="Short paragraph describing what works well in the taxonomy.",
    )
    gaps_or_risks: str = Field(
        ...,
        description=(
            "Short paragraph calling out missing areas, redundancy, or hierarchy issues."
        ),
    )
    action_items: list[str] = Field(
        default_factory=list,
        description="Concise bullet-style suggestions to improve the taxonomy.",
    )


class State(BaseModel):
    works: list[dict] = Field(
        ..., description="A list of works with title and abstract."
    )
    taxonomy_list: list[Taxonomy] = Field(
        default_factory=list,
        description="The generated taxonomy from the works.",
    )
    merged_taxonomy: Taxonomy | None = Field(
        default=None,
        description="A single taxonomy merged from the generated batches.",
    )
    evaluation_report: TaxonomyEvaluation | None = Field(
        default=None,
        description="Evaluation metadata for the merged taxonomy.",
    )

def taxonomy_to_tree(taxonomy: Taxonomy) -> Tree:
    tree = Tree()
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
    Your task is to create a taxonomy from research documents that consist
    of title and abstracts.

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
    Combine the provided taxonomy JSON payloads into one taxonomy that
    captures all relevant topics without duplication.

    # Guidelines
        - Preserve meaningful distinctions between categories; merge overlapping
            concepts instead of repeating them.
    - Ensure the hierarchy remains balanced and avoids redundant nesting.
    - Keep descriptions concise and grounded in the source category descriptions.

    # Output Format
    Return a single taxonomy following this JSON schema:
    {Taxonomy.model_json_schema()}
    """
)


TAXONOMY_EVALUATION_SYSTEM_PROMPT = dedent(
        f"""
        You are a rigorous evaluator of technology taxonomies derived from research works.

        # Task
        Review the provided taxonomy JSON and score it using the following criteria:
            1. Coverage: Does it capture the breadth of concepts present in the source works?
            2. Structure: Is the hierarchy balanced with meaningful parent/child relationships?
            3. Description Quality: Do category descriptions clearly communicate the scope?

        # Expectations
        - Reference specific hierarchy patterns when praising or critiquing the taxonomy.
        - Flag redundant, overlapping, or missing categories.
        - Keep suggestions actionable so the author can iterate quickly.

        # Output Format
        Respond using this JSON schema:
        {TaxonomyEvaluation.model_json_schema()}
        """
)





class TaxonomyPipeline:
    """High-level orchestration for generating and merging taxonomies."""

    def __init__(
        self,
        llm: ChatOpenAI,
        batch_size: int,
        store: InMemoryStore,
    ) -> None:
        self.llm = llm
        self.batch_size = batch_size
        self.store = store

        self.taxonomy_agent = self._create_taxonomy_agent()
        self.merge_agent = self._create_merge_agent()
        self.evaluation_agent = self._create_evaluation_agent()
        self.last_evaluation = None
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

    def _create_evaluation_agent(self):
        return create_agent(
            model=self.llm,
            system_prompt=TAXONOMY_EVALUATION_SYSTEM_PROMPT,
            response_format=ProviderStrategy(TaxonomyEvaluation),
        )

    def _build_graph(self):
        graph_builder = StateGraph(State)
        graph_builder.add_node("generate_taxonomy", self._generate_taxonomy)
        graph_builder.add_node("merge_taxonomy", self._merge_taxonomy)
        graph_builder.add_node("evaluate_taxonomy", self._evaluate_taxonomy)
        
        graph_builder.add_edge(START, "generate_taxonomy")
        graph_builder.add_edge("generate_taxonomy", "merge_taxonomy")
        graph_builder.add_edge("merge_taxonomy", "evaluate_taxonomy")
        graph_builder.add_edge("evaluate_taxonomy", END)
        
        return graph_builder.compile(store=self.store)

    def _generate_taxonomy(
        self,
        state: State,
        _config: RunnableConfig | None = None,
    ) -> dict:
        """Run the taxonomy agent across works converted into batched messages."""

        batch_size = self.batch_size
        if not state.works:
            return {"taxonomy_list": []}

        texts = [self._format_prompt_block(work) for work in state.works]
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

    def _merge_taxonomy(self, state: State) -> dict:
        """Merge multiple taxonomy batches into a single taxonomy."""

        if not state.taxonomy_list:
            return {"merged_taxonomy": None, "taxonomy_list": []}

        serialized_batches = [
            f"Taxonomy {index}:\n{taxonomy.model_dump_json(indent=2)}"
            for index, taxonomy in enumerate(state.taxonomy_list, start=1)
        ]
        prompt_value = ChatPromptValue(
            messages=[
                SystemMessage(
                    content=(
                        "You are an expert editor. Merge overlapping categories and ensure a coherent hierarchy."
                    ),
                ),
                HumanMessage(
                    content=(
                        "Merge the following taxonomy batches into a single taxonomy JSON. "
                        "Return only valid JSON matching the schema:\n"
                        f"{''.join(serialized_batches)}"
                    ),
                ),
            ]
        )
        response = self.taxonomy_agent.invoke(prompt_value)
        merged_taxonomy = response.get("structured_response")

        return {
            "merged_taxonomy": merged_taxonomy,
            "taxonomy_list": [merged_taxonomy],
        }
    def _evaluate_taxonomy(self, state: State) -> dict:
        """Score the merged taxonomy and surface actionable feedback."""

        if not state.merged_taxonomy:
            return {"evaluation_report": None}

        serialized_taxonomy = state.merged_taxonomy.model_dump_json(indent=2)
        prompt_value = ChatPromptValue(
            messages=[
                HumanMessage(
                    content=(
                        "Evaluate the following taxonomy JSON and provide a structured report:\n"
                        f"{serialized_taxonomy}"
                    ),
                )
            ]
        )
        
        response = self.evaluation_agent.batch([prompt_value])[0]
        structured = response.get("structured_response")

        if structured is None:
            return {"evaluation_report": None}

        evaluation = (
            structured
            if isinstance(structured, TaxonomyEvaluation)
            else TaxonomyEvaluation.model_validate(structured)
        )

        return {"evaluation_report": evaluation}

    def run(
        self,
        works: list[dict],
    ) -> Taxonomy | None:
        """Execute the taxonomy graph and return the merged taxonomy."""
        taxonomy, _ = self.run_with_evaluation(works)
        return taxonomy

    def run_with_evaluation(
        self,
        works: list[dict],
    ) -> tuple[Taxonomy | None, TaxonomyEvaluation | None]:
        """Execute the graph and return both taxonomy and evaluation report."""

        state = self._invoke_graph(works)
        evaluation = state.get("evaluation_report")
        self.last_evaluation = evaluation
        return state["merged_taxonomy"], evaluation

    def _invoke_graph(
        self,
        works: list[dict],
    ) -> State:
        normalized_works = [self._normalize_document(work) for work in works]
        if normalized_works:
            self._persist_documents(normalized_works)
        return self.graph.invoke(
            {
                "works": normalized_works,
                "taxonomy_list": [],
                "merged_taxonomy": None,
                "evaluation_report": None,
            },
        )

    def _format_prompt_block(self, document: dict) -> str:
        title = document.get("title") or "Untitled"
        abstract = document.get("abstract") or ""
        return f"Title: {title}\nAbstract: {abstract}"



    def _extract_value(
        self,
        data: dict,
        configured_field: str,
        *,
        fallbacks: tuple[str, ...],
    ) -> str:
        candidates = (configured_field, *fallbacks)
        for field in candidates:
            value = data.get(field)
            if value:
                return str(value)
        return ""



def load_works(data_path) -> list[dict]:
    """Load works data from a JSONL file."""
    return pd.read_json(data_path, lines=True).to_dict(orient="records")



llm = ChatOpenAI(model="gpt-5-mini")



