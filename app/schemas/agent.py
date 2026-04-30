from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    input_text: str = Field(..., min_length=1)


class AgentRunResponse(BaseModel):
    id: int
    input_text: str
    output_text: str


class ToolLogResponse(BaseModel):
    id: int
    tool_name: str
    tool_input: dict | None
    tool_output: dict | None
    status: str
    error_message: str | None