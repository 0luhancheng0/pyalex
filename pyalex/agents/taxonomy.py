from __future__ import annotations
from typing import Annotated
from collections.abc import Callable
from itertools import count
from pathlib import Path
from textwrap import dedent
from uuid import uuid4
import operator
import pandas as pd
from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langchain_core.prompt_values import ChatPromptValue
from langchain_openai import ChatOpenAI
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
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
    
    def as_tree(self) -> Tree:
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

        for top_level in self.category_list:
            _add_category(top_level, "taxonomy")

        return tree

    def as_json(self):
        return self.as_tree().to_json(with_data=True)

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


class WorkClassification(BaseModel):
    work_id: str = Field(
        ...,
        description="Stable identifier for the work being classified.",
    )
    title: str = Field(
        ...,
        description="Title of the work for quick reference.",
    )
    categories: list[str] = Field(
        default_factory=list,
        description="List of taxonomy category paths assigned to the work.",
    )
    rationale: str = Field(
        ...,
        description="Short explanation citing evidence from the work.",
    )


class State(BaseModel):
    works: list[dict] = Field(
        ..., description="A list of works with title and abstract."
    )
    messages: Annotated[list[ChatPromptValue], operator.add] = Field(
        default_factory=list,
        description="Batched prompt payloads fed into the taxonomy generator.",
    )
    taxonomy_list: Annotated[list[Taxonomy], operator.add] = Field(
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
    work_classifications: list[WorkClassification] = Field(
        default_factory=list,
        description="Multi-label assignments of taxonomy categories to works.",
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


CLASSIFICATION_AGENT_SYSTEM_PROMPT = dedent(
    f"""
    You map research works to one or more categories from a provided taxonomy.

    - Use only the category names (or full breadcrumb paths) that appear in the taxonomy inventory.
    - If a work does not fit any category, return an empty list for categories.
    - Keep rationales concise and reference evidence from the work text.

    Respond using this JSON schema:
    {WorkClassification.model_json_schema()}
    """
)





class TaxonomyPipeline:
    """High-level orchestration for generating and merging taxonomies."""

    def __init__(
        self,
        llm: ChatOpenAI,
        batch_size: int,
        abstract_key: str
    ) -> None:
        self.llm = llm
        self.batch_size = batch_size

        self.taxonomy_agent = self._create_taxonomy_agent()
        self.merge_agent = self._create_merge_agent()
        self.evaluation_agent = self._create_evaluation_agent()
        self.classification_agent = self._create_classification_agent()
        self.last_evaluation = None
        self.abstract_key = abstract_key
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

    def _create_classification_agent(self):
        return create_agent(
            model=self.llm,
            system_prompt=CLASSIFICATION_AGENT_SYSTEM_PROMPT,
            response_format=ProviderStrategy(WorkClassification),
        )

    def _build_graph(self):
        graph_builder = StateGraph(State)
        graph_builder.add_node("create_messages", self._create_messages)
        graph_builder.add_node("generate_taxonomy", self._generate_taxonomy)
        graph_builder.add_node("merge_taxonomy", self._merge_taxonomy)
        graph_builder.add_node("evaluate_taxonomy", self._evaluate_taxonomy)
        graph_builder.add_node("classify_works", self._classify_works)
        
        graph_builder.add_edge(START, "create_messages")
        graph_builder.add_edge("create_messages", "generate_taxonomy")
        graph_builder.add_edge("generate_taxonomy", "merge_taxonomy")
        graph_builder.add_edge("merge_taxonomy", "evaluate_taxonomy")
        graph_builder.add_edge("evaluate_taxonomy", "classify_works")
        graph_builder.add_edge("classify_works", END)
        
        return graph_builder.compile()

    def _create_messages(self, state: State) -> list[ChatPromptValue]:
        texts = [self._format_prompt_block(work) for work in state.works]
        batches = [texts[i : i + self.batch_size] for i in range(0, len(texts), self.batch_size)]
        batch_texts = ["\n\n".join(batch) for batch in batches]
        messages = [
            ChatPromptValue(messages=[HumanMessage(content=batch_text)])
            for batch_text in batch_texts
        ]
        return {"messages": messages}

    def _generate_taxonomy(
        self,
        state: State,
    ) -> dict:
        """Run the taxonomy agent across works converted into batched messages."""

        taxonomy_list = self.taxonomy_agent.batch(state.messages)
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

    def _classify_works(self, state: State) -> dict:
        if not state.merged_taxonomy or not state.works:
            return {"work_classifications": []}

        taxonomy = state.merged_taxonomy
        inventory = self._flatten_category_paths(taxonomy)
        inventory_block = "\n".join(f"- {label}" for label in inventory)
        taxonomy_json = taxonomy.model_dump_json(indent=2)

        messages: list[ChatPromptValue] = []
        metadata: list[tuple[str, str]] = []

        for work in state.works:
            work_id = self._resolve_work_id(work)
            title = (work.get("title") or "Untitled").strip()
            abstract = (work.get(self.abstract_key) or "").strip()
            metadata.append((work_id, title))
            content = dedent(
                f"""
                Use the taxonomy below to assign zero or more categories to the work. Only pick from the
                provided inventory. If nothing fits, return an empty list.

                Taxonomy JSON:
                {taxonomy_json}

                Category inventory:
                {inventory_block}

                Work ID: {work_id}
                Title: {title}
                Abstract: {abstract}
                """
            ).strip()
            messages.append(
                ChatPromptValue(
                    messages=[
                        HumanMessage(content=content),
                    ]
                )
            )

        responses = self.classification_agent.batch(messages)
        inventory_set = {label for label in inventory}
        inventory_leafs = {label.split(" > ")[-1] for label in inventory}
        classifications: list[WorkClassification] = []

        for (work_id, title), response in zip(metadata, responses, strict=True):
            classification = response.get("structured_response")

            filtered_categories = []
            for category in classification.categories:
                normalized = category.strip()
                if not normalized:
                    continue
                if normalized in inventory_set or normalized.split(" > ")[-1] in inventory_leafs:
                    filtered_categories.append(normalized)
            classifications.append(
                WorkClassification(
                    work_id=work_id,
                    title=title,
                    categories=filtered_categories,
                    rationale=classification.rationale,
                )
            )

        return {"work_classifications": classifications}


    def run(
        self,
        works: list[dict],
    ) -> State:
        return self.graph.invoke(
            {
                "works": works,
                "messages": [],
                "taxonomy_list": [],
                "merged_taxonomy": None,
                "evaluation_report": None,
                "work_classifications": [],
            },
        )

    def _format_prompt_block(self, document: dict) -> str:
        title = document.get("title") or ""
        abstract = document.get(self.abstract_key) or ""
        return f"Title: {title}\nAbstract: {abstract}"

    def _flatten_category_paths(self, taxonomy: Taxonomy) -> list[str]:
        paths: list[str] = []

        def _visit(category: Category, ancestors: tuple[str, ...]) -> None:
            path = " > ".join((*ancestors, category.name)) if ancestors else category.name
            paths.append(path)
            for child in category.subcategories:
                _visit(child, (*ancestors, category.name))

        for top_level in taxonomy.category_list:
            _visit(top_level, ())
        return paths

    def _resolve_work_id(self, work: dict) -> str:
        for candidate in ("id", "work_id", "grant_id"):
            value = work.get(candidate)
            if value:
                return str(value)
        return uuid4().hex



works = pd.read_json("/Users/luhancheng/research-link-technology-landscaping/modeling/results/grants.jsonl", lines=True).to_dict(orient="records")


llm = ChatOpenAI(model="Qwen/Qwen3-4B-Instruct-2507", base_url="http://localhost:8000/v1")

pipeline = TaxonomyPipeline(llm=llm, batch_size=5, abstract_key="grant_summary")

state = pipeline.run(works[:10])


state["work_classifications"]

