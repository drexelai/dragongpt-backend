import os
import uuid
import json
import ast
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
from typing import List, TypedDict, Optional
from pydantic import BaseModel, Field
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)

load_dotenv(dotenv_path='.env.local')

df = pd.read_csv('data_collection/tms/winter-tms.csv')
engine = create_engine("sqlite:///course_scheduler/winterTms.db")
db = SQLDatabase(engine=engine)

#df.to_sql("winterTms", engine, index=False)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert extraction algorithm. "
            "Only extract relevant information from the text. "
            "If you do not know the value of an attribute asked "
            "to extract, return null for the attribute's value.",
        ),
        MessagesPlaceholder("examples"),
        ("human", "{text}"),
    ]
)

class SubjectCoursePair(BaseModel):
    subject: str = Field(..., description="The subject code of the course (e.g., 'CS').")
    course: int = Field(..., description="The course number (e.g., 101).")

class TMS(BaseModel):
    subject_course_pairs: List[SubjectCoursePair] = Field(..., description="A list of subject and course pairs")
    excluded_days: List[str] = Field(..., description="A list of days to exclude for scheduling")
    start_time_limit: Optional[int] = Field(..., description="The earliest time (in 24-hour format) a course can start")

class Data(BaseModel):
    people: List[TMS]

class Example(TypedDict):
    input: str
    tool_calls: List[BaseModel]

def tool_example_to_messages(example: Example) -> List[BaseMessage]:
    messages: List[BaseMessage] = [HumanMessage(content=example["input"])]
    openai_tool_calls = []
    for tool_call in example["tool_calls"]:
        openai_tool_calls.append(
            {
                "id": str(uuid.uuid4()),
                "type": "function",
                "function": {
                    "name": tool_call.__class__.__name__,
                    "arguments": tool_call.model_dump_json(),
                },
            }
        )
    messages.append(
        AIMessage(content="", additional_kwargs={"tool_calls": openai_tool_calls})
    )
    tool_outputs = example.get("tool_outputs") or [
        "You have correctly called this tool."
    ] * len(openai_tool_calls)
    for output, tool_call in zip(tool_outputs, openai_tool_calls):
        messages.append(ToolMessage(content=output, tool_call_id=tool_call["id"]))
    return messages
