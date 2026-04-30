from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_db_session,
    get_embedder,
    get_feature_columns,
    get_http_client,
    get_ml_model,
)
from app.schemas.tools import ToolCallRequest, ToolCallResponse, ToolInfo
from app.services.tool_runner import ToolRuntimeContext, run_tool
from app.tools.registry import is_tool_allowed, list_tools

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
    session: AsyncSession = Depends(get_db_session),
):
    if not is_tool_allowed(request.tool_name):
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{request.tool_name}' was not found.",
        )

    result = await run_tool(
        tool_name=request.tool_name,
        raw_args=request.arguments,
        context=ToolRuntimeContext(
            model=model,
            feature_columns=feature_columns,
            embedder=embedder,
            http_client=http_client,
            session=session,
        ),
    )

    if result["status"] == "failed":
        raise HTTPException(
            status_code=422,
            detail={
                "tool_name": request.tool_name,
                "status": result["status"],
                "error_message": result["error_message"],
            },
        )

    return {
        "tool_name": request.tool_name,
        "result": result["tool_output"],
    }
