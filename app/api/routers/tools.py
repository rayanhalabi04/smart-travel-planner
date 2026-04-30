import inspect
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.dependencies import (
    get_embedder,
    get_feature_columns,
    get_http_client,
    get_ml_model,
)
from app.schemas.tools import ToolCallRequest, ToolCallResponse, ToolInfo
from app.tools.registry import get_tool, list_tools

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.get("/list", response_model=list[ToolInfo])
def list_available_tools():
    return list_tools()


@router.post("/call", response_model=ToolCallResponse)
async def call_tool(
    request: ToolCallRequest,
    model: Any = Depends(get_ml_model),
    feature_columns: list[str] = Depends(get_feature_columns),
    embedder: Any = Depends(get_embedder),
    http_client: Any = Depends(get_http_client),
):
    settings = get_settings()

    tool = get_tool(request.tool_name)

    if tool is None:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{request.tool_name}' was not found.",
        )

    result = tool(
        arguments=request.arguments,
        model=model,
        feature_columns=feature_columns,
        embedder=embedder,
        http_client=http_client,
        chroma_path=settings.chroma_path,
        collection_name=settings.chroma_collection_name,
        top_k=settings.rag_top_k,
        geocoding_url=settings.weather_geocoding_url,
        forecast_url=settings.weather_base_url,
    )

    if inspect.isawaitable(result):
        result = await result

    return {
        "tool_name": request.tool_name,
        "result": result,
    }