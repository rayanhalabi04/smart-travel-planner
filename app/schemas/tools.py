from typing import Any

from pydantic import BaseModel


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any]


class ToolCallResponse(BaseModel):
    tool_name: str
    result: dict[str, Any]


class ToolInfo(BaseModel):
    name: str
    description: str
    required_arguments: list[str]