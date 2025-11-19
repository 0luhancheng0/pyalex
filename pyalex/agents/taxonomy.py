import operator
from textwrap import dedent
from typing import Annotated, Union
from uuid import uuid4
import graph_tool.all as gt
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
from pydantic import ConfigDict
from pydantic import Field
    

class CategoryModel(BaseModel):
    name: str = Field(..., description="The name of the category.")
    description: str = Field(..., description="A brief description of the category.")
    subcategories: list["CategoryModel"] = Field(
        default_factory=list,
        description=(
            "A list of subcategories. Empty if the current category is a leaf node."
        ),
    )


class TaxonomyModel(BaseModel):
    category_list: list[CategoryModel] = Field(
        ...,
        description="A list of taxonomy items in nested bullet point format.",
    )


    def flatten(self) -> list[str]:
        paths: list[str] = []

        def _visit(category: CategoryModel, ancestors: tuple[str, ...]) -> None:
            path = (
                " > ".join((*ancestors, category.name)) if ancestors else category.name
            )
            paths.append(path)
            for child in category.subcategories:
                _visit(child, (*ancestors, category.name))

        for top_level in self.category_list:
            _visit(top_level, ())
        return paths


class TaxonomyEvaluationModel(BaseModel):
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
    model_config = ConfigDict(arbitrary_types_allowed=True)

    works: list[dict] = Field(
        ..., description="A list of works with title and abstract."
    )
    messages: Annotated[list[ChatPromptValue], operator.add] = Field(
        default_factory=list,
        description="Batched prompt payloads fed into the taxonomy generator.",
    )
    taxonomy_list: Annotated[list[TaxonomyModel], operator.add] = Field(
        default_factory=list,
        description="The generated taxonomy from the works.",
    )
    merged_taxonomy: TaxonomyModel | None = Field(
        default=None,
        description="A single taxonomy merged from the generated batches.",
    )
    evaluation_report: TaxonomyEvaluationModel | None = Field(
        default=None,
        description="Evaluation metadata for the merged taxonomy.",
    )
    work_classifications: list[WorkClassification] = Field(
        default_factory=list,
        description="Multi-label assignments of taxonomy categories to works.",
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
    {TaxonomyModel.model_json_schema()}
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
        {TaxonomyEvaluationModel.model_json_schema()}
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




class GenerateTaxonomy:
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
        {TaxonomyModel.model_json_schema()}
        """
    )
    def __init__(self, llm: ChatOpenAI) -> None:
        self.llm = llm
        self.taxonomy_agent = self._create_taxonomy_agent()
        
    def _create_taxonomy_agent(self):
        return create_agent(
            model=self.llm,
            system_prompt=GenerateTaxonomy.TAXONOMY_AGENT_SYSTEM_PROMPT,
            response_format=ProviderStrategy(TaxonomyModel),
        )
    def __call__(self, state: State):
        taxonomy_list = self.taxonomy_agent.batch(state.messages)
        structured_responses = [
            response["structured_response"] for response in taxonomy_list
        ]
        return {"taxonomy_list": structured_responses}


class CreateMessages:
    def __init__(self, batch_size: int, abstract_key: str) -> None:
        self.batch_size = batch_size
        self.abstract_key = abstract_key

    def __call__(self, state: State) -> dict:
        texts = [self._format_prompt_block(work) for work in state.works]
        batches = [
            texts[i : i + self.batch_size]
            for i in range(0, len(texts), self.batch_size)
        ]
        batch_texts = ["\n\n".join(batch) for batch in batches]
        messages = [
            ChatPromptValue(messages=[HumanMessage(content=batch_text)])
            for batch_text in batch_texts
        ]
        return {"messages": messages}

    def _format_prompt_block(self, document: dict) -> str:
        title = document.get("title") or ""
        abstract = document.get(self.abstract_key) or ""
        return f"Title: {title}\nAbstract: {abstract}"


class MergeTaxonomy:
    def __init__(self, llm: ChatOpenAI) -> None:
        self.llm = llm
        self.agent = self._create_merge_agent()

    def __call__(self, state: State) -> dict:
        if not state.taxonomy_list:
            return {
                "merged_taxonomy": None,
                "taxonomy_list": [],
                "taxonomy_graph": None,
            }

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
        response = self.agent.invoke(prompt_value)
        merged_taxonomy = response.get("structured_response")
        return {"merged_taxonomy": merged_taxonomy}

    def _create_merge_agent(self):
        return create_agent(
            model=self.llm,
            system_prompt=TAXONOMY_MERGE_AGENT_SYSTEM_PROMPT,
            response_format=ProviderStrategy(TaxonomyModel),
        )


class EvaluateTaxonomy:
    def __init__(self, llm: ChatOpenAI) -> None:
        self.llm = llm
        self.agent = self._create_evaluation_agent()

    def __call__(self, state: State) -> dict:
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
        response = self.agent.batch([prompt_value])[0]
        evaluation = response.get("structured_response")
        return {"evaluation_report": evaluation}

    def _create_evaluation_agent(self):
        return create_agent(
            model=self.llm,
            system_prompt=TAXONOMY_EVALUATION_SYSTEM_PROMPT,
            response_format=ProviderStrategy(TaxonomyEvaluationModel),
        )


class ClassifyWorks:
    def __init__(self, llm: ChatOpenAI, abstract_key: str) -> None:
        self.llm = llm
        self.agent = self._create_classification_agent()
        self.abstract_key = abstract_key
    def __call__(self, state: State) -> dict:
        
        if not state.merged_taxonomy:
            return {"work_classifications": []}

        serialized_taxonomy = state.merged_taxonomy.model_dump_json(indent=2)
        classifications = []
        prompts: list[ChatPromptValue] = []
        for work in state.works:
            title = work.get("title") or ""
            abstract = work.get(self.abstract_key) or ""
            work_id = work.get("id")
            prompt_value = ChatPromptValue(
                messages=[
                    SystemMessage(
                        content=(
                            f"Here is the taxonomy to classify against:\n{serialized_taxonomy}"
                        ),
                    ),
                    HumanMessage(
                        content=(
                            f"Classify the following work into the taxonomy categories.\n"
                            f"ID: {work_id}\nTitle: {title}\nAbstract: {abstract}"
                        ),
                    ),
                ]
            )
            prompts.append(prompt_value)
            
        response = self.agent.batch(prompts)
        classifications = [i.get("structured_response") for i in response]
        return {"work_classifications": classifications}
    
    def _create_classification_agent(self):
        return create_agent(
            model=self.llm,
            system_prompt=CLASSIFICATION_AGENT_SYSTEM_PROMPT,
            response_format=ProviderStrategy(WorkClassification),
        )

class TaxonomyPipeline:
    """High-level orchestration for generating and merging taxonomies."""

    def __init__(self, llm: ChatOpenAI, batch_size: int, abstract_key: str) -> None:
        self.llm = llm
        self.batch_size = batch_size
        self.abstract_key = abstract_key
        self.generate_taxonomy = GenerateTaxonomy(llm=self.llm)
        self.create_messages = CreateMessages(
            batch_size=self.batch_size, abstract_key=self.abstract_key
        )
        self.merge_taxonomy = MergeTaxonomy(self.llm)
        self.evaluate_taxonomy = EvaluateTaxonomy(self.llm)
        self.classify_works = ClassifyWorks(self.llm, abstract_key=self.abstract_key)
        self.last_evaluation = None
        self.graph = self._build_graph()

    def _build_graph(self):
        graph_builder = StateGraph(State)
        graph_builder.add_node("create_messages", self.create_messages)
        graph_builder.add_node("generate_taxonomy", self.generate_taxonomy)
        graph_builder.add_node("merge_taxonomy", self.merge_taxonomy)
        graph_builder.add_node("evaluate_taxonomy", self.evaluate_taxonomy)
        graph_builder.add_node("classify_works", self.classify_works)

        graph_builder.add_edge(START, "create_messages")
        graph_builder.add_edge("create_messages", "generate_taxonomy")
        graph_builder.add_edge("generate_taxonomy", "merge_taxonomy")
        graph_builder.add_edge("merge_taxonomy", "evaluate_taxonomy")
        graph_builder.add_edge("evaluate_taxonomy", "classify_works")
        graph_builder.add_edge("classify_works", END)

        return graph_builder.compile()

    def input_state(self, works):
        return State(
            works=works,
            messages=[],
            taxonomy_list=[],
            merged_taxonomy=None,
            evaluation_report=None,
            work_classifications=[],
            taxonomy_graph=None,
        )
    def run(
        self,
        works: list[dict],
    ) -> State:
        return self.graph.invoke(self.input_state(works=works))


works = pd.read_json(
    "/Users/luhancheng/research-link-technology-landscaping/modeling/results/grants.jsonl",
    lines=True,
).to_dict(orient="records")

# llm = ChatOpenAI(model="Qwen/Qwen3-4B-Instruct-2507", base_url="http://localhost:8000/v1")
llm = ChatOpenAI(model="gpt-5-mini")

pipeline = TaxonomyPipeline(llm=llm, batch_size=5, abstract_key="grant_summary")


state = pipeline.run(works[:10])

taxonomy = state["merged_taxonomy"].model_dump()

g = gt.Graph()

def traverse(category: Union[dict, list]):
    if isinstance(category, dict):
        print(category["name"])
        for subcategory in category.get("subcategories", []):
            traverse(subcategory)
    else:
        for cat in category:
            traverse(cat)

traverse(taxonomy["category_list"])

