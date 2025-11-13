"""Technology landscaping agents powered by LangChain."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import MutableMapping
from collections.abc import Sequence
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from textwrap import dedent
from typing import Any

import pandas as pd
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import HumanMessagePromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langgraph.channels.binop import BinaryOperatorAggregate
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph

PROMPT_DESIGNER_PROMPT = ChatPromptTemplate(
    messages=[
        SystemMessage(
            content=dedent(
                """
                You are an expert prompt engineer collaborating on a technology landscaping workflow.
                Your task is to design a prompt that will be used as the system prompt for a large language model that extracts a specific aspect from a research publication.
                Craft a concise system prompt (no prepended commentary) that will instruct an assistant to excel at extracting this aspect. Return only the system prompt text.
                In the prompt, specify that the output must be a single string rather than structured output.
                """
            ).strip(),
        ),
        HumanMessagePromptTemplate.from_template(
            dedent(
                """
                Please provide the system prompt for extracting the {aspect_name} aspect.
                Aspect: {aspect_name}
                Aspect objective: {aspect_description}
                """
            ).strip(),
        ),
    ]
)


ASPECT_AGENT_USER_TEMPLATE = dedent(
    """
    Here is the input publication:
    Title: {title}
    Abstract: {abstract}
    """
).strip()


@dataclass
class AspectDefinition:
    """Describe a publication aspect to be extracted by the workflow."""

    aspect_name: str
    aspect_description: str


DEFAULT_ASPECTS = [
    AspectDefinition(
        aspect_name="objective",
        aspect_description="Objective of a research work. They should focus on the problem addressed and the intended contribution.",
    ),
    AspectDefinition(
        aspect_name="outcomes",
        aspect_description="Outcomes of a research work. They may include key results, validations, or conclusions.",
    ),
    AspectDefinition(
        aspect_name="methods",
        aspect_description="Methods used in a research work. They may include approaches, datasets, architectures, or techniques.",
    ),
    AspectDefinition(
        aspect_name="readiness",
        aspect_description=(
            "Classify the maturity of the technology as concept, laboratory validation, pilot deployment, or production-ready and "
            "justify the classification in one sentence."
        ),
    ),
]


DEFAULT_LLM_MODEL = "gpt-5-mini"


@dataclass
class State:
    """Track the evolving state for the LangGraph orchestration."""

    id: str | None = None
    title: str = ""
    abstract: str = ""
    aspects: MutableMapping[str, str] = field(default_factory=dict)


def build_prompt_designer(llm: ChatOpenAI) -> Runnable:
    """Create the runnable that designs aspect-specific system prompts."""

    return RunnableLambda(asdict) | PROMPT_DESIGNER_PROMPT | llm | StrOutputParser()


def build_aspect_agent(aspect_name: str, system_prompt: str, llm: ChatOpenAI) -> Runnable:
    """Create a runnable that extracts a single aspect from a publication."""

    prompt_template = ChatPromptTemplate(
        messages=[
            SystemMessage(content=system_prompt),
            HumanMessagePromptTemplate.from_template(ASPECT_AGENT_USER_TEMPLATE),
        ]
    )

    def _attach_aspect(result: str) -> dict[str, dict[str, str]]:
        return {"aspects": {aspect_name: result}}

    return RunnableLambda(asdict) | prompt_template | llm | StrOutputParser() | RunnableLambda(_attach_aspect)


def build_state_graph(aspect_agents: Sequence[tuple[AspectDefinition, Runnable]]) -> Runnable:
    """Wire the aspect agents into a LangGraph state machine."""

    graph_builder = StateGraph(State)
    graph_builder.channels["aspects"] = BinaryOperatorAggregate(dict, lambda current, update: {**current, **update})

    for aspect, agent in aspect_agents:
        node_name = f"{aspect.aspect_name}_agent"
        graph_builder.add_node(node_name, agent)
        graph_builder.add_edge(START, node_name)
        graph_builder.add_edge(node_name, END)

    return graph_builder.compile()


class LandscapingWorkflow:
    """Orchestrate prompt generation and aspect extraction for publications."""

    def __init__(
        self,
        aspects: Sequence[AspectDefinition] | None = None,
        *,
        llm: ChatOpenAI | None = None,
    ) -> None:
        self.aspects = list(aspects) if aspects is not None else list(DEFAULT_ASPECTS)
        self.llm = llm or ChatOpenAI(model=DEFAULT_LLM_MODEL)

        prompt_designer = build_prompt_designer(self.llm)
        prompt_texts = prompt_designer.batch(self.aspects)
        self._aspect_prompts = {
            aspect.aspect_name: prompt for aspect, prompt in zip(self.aspects, prompt_texts, strict=True)
        }

        aspect_agents = [
            (aspect, build_aspect_agent(aspect.aspect_name, self._aspect_prompts[aspect.aspect_name], self.llm))
            for aspect in self.aspects
        ]

        self._graph = build_state_graph(aspect_agents)

    @property
    def prompts(self) -> dict[str, str]:
        """Return the generated system prompts per aspect."""

        return dict(self._aspect_prompts)

    def run_dataframe(
        self,
        df: pd.DataFrame,
        *,
        limit: int | None = None,
        config: RunnableConfig | None = None,
    ) -> pd.DataFrame:
        """Execute the workflow for rows in a dataframe."""

        records = df.to_dict(orient="records")
        return self.run_records(records, limit=limit, config=config)

    def run_records(
        self,
        records: Sequence[Mapping[str, Any]],
        *,
        limit: int | None = None,
        config: RunnableConfig | None = None,
    ) -> pd.DataFrame:
        """Execute the workflow for an arbitrary sequence of publication records."""

        record_list = list(records)
        if limit is not None:
            record_list = record_list[:limit]

        states = [self._state_from_record(record, index) for index, record in enumerate(record_list)]

        if config is not None:
            responses = self._graph.batch(states, config=config)
        else:
            responses = self._graph.batch(states)

        return pd.DataFrame(responses)

    @staticmethod
    def aspects_dataframe(responses_df: pd.DataFrame) -> pd.DataFrame:
        """Expand the aspects column into a dedicated dataframe."""

        if "aspects" not in responses_df:
            raise KeyError("responses_df is missing the 'aspects' column")

        aspects = pd.DataFrame(responses_df["aspects"].tolist())
        if "id" in responses_df:
            aspects["id"] = responses_df["id"]
        return aspects.set_index("id") if "id" in aspects else aspects

    @staticmethod
    def _state_from_record(record: Mapping[str, Any], fallback_id: int) -> State:
        try:
            title = record["title"]
            abstract = record["abstract"]
        except KeyError as exc:  # pragma: no cover - defensive clarity
            missing = exc.args[0]
            raise KeyError(f"Record missing required field '{missing}'") from exc

        identifier = record.get("id", fallback_id)
        identifier_str = str(identifier) if identifier is not None else str(fallback_id)

        return State(id=identifier_str, title=title, abstract=abstract)

df = pd.read_json("/Users/luhancheng/pyalex/data/2024.jsonl", lines=True)
workflow = LandscapingWorkflow()
response = workflow.run_dataframe(df, limit=3)
aspects_df = workflow.aspects_dataframe(response)

