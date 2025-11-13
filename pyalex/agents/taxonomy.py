import asyncio
from dataclasses import dataclass
from itertools import count
from textwrap import dedent
from langchain_core.runnables.config import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import HumanMessagePromptTemplate
from langchain_core.prompt_values import ChatPromptValue
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from pydantic import Field
from treelib import Tree
from langchain.agents.structured_output import ProviderStrategy
from pyalex import Works
from langchain.agents import create_agent
import operator
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
import pandas as pd


class Category(BaseModel):
    name: str = Field(..., description="The name of the category.")
    description: str = Field(..., description="A brief description of the category.")
    subcategories: list["Category"] = Field(
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
    works: Annotated[list[dict], operator.add] = Field(..., description="A list of works with title and abstract.")
    messages: list[ChatPromptValue] = Field(..., description="A list of text messages.", default_factory=list)
    taxonomy_list: Annotated[list[Taxonomy], operator.add] = Field(..., description="The generated taxonomy from the works.", default_factory=list)
    

def taxonomy_to_tree(taxonomy: Taxonomy) -> Tree:

    tree = Tree()
    tree.create_node("Taxonomy", "taxonomy")

    def _add_category(category: Category, parent_id: str) -> None:
        tree.create_node(category.name, category.name, parent=parent_id, data=category)
        for child in category.subcategories:
            _add_category(child, category.name)

    for top_level in taxonomy.category_list:
        _add_category(top_level, "taxonomy")

    return tree

llm = ChatOpenAI(model="gpt-5-mini")

taxonomy_agent = create_agent(
    model=llm,
    system_prompt=dedent(f"""
        You are an expert engineer collaborating on a
        technology landscaping workflow.

        # Objective
        Your task is to create a taxonomy from research
        documents that consist of title and abstracts.

        # Constraints
        - Your taxonomy should be hierarchical and cover the major topics found in the documents.
        - Skip any topic that does not appear in the source documents.
        - Give each category a name and a brief description.
        - Do NOT include the input documents as taxonomy entries.

        # Output Format
        Here is the model json schema describing the output format you should follow:
        {Taxonomy.model_json_schema()}
        """
    ).strip(),
    response_format=ProviderStrategy(Taxonomy)
)

def build_messages(state: State, config: RunnableConfig) -> dict:
    texts = [f"Title: {work['title']}\nAbstract: {work['abstract']}" for work in state.works]
    batch_size = config['metadata']['batch_size']
    batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
    batch_texts = ["\n\n".join(batch) for batch in batches]
    messages = list(map(lambda x: ChatPromptValue(messages=[x]), map(HumanMessage, batch_texts)))
    return {"messages": list(messages)}


def generate_taxonomy(state: State) -> dict:
    taxonomy_list = taxonomy_agent.batch(state.messages)
    return {"taxonomy_list": [i['structured_response'] for i in taxonomy_list]}


works = pd.read_json("/Users/luhancheng/pyalex/data/2025.jsonl", lines=True).to_dict(orient="records")

graph_builder = StateGraph(State)
graph_builder.add_node("build_messages", build_messages)
graph_builder.add_node("generate_taxonomy", generate_taxonomy)


graph_builder.add_edge(START, "build_messages")
graph_builder.add_edge("build_messages", "generate_taxonomy")
graph_builder.add_edge("generate_taxonomy", END)
graph = graph_builder.compile()


state = graph.invoke({"works": works, "messages": [], "taxonomy_list": []}, config={"metadata": {"batch_size": 20}})

