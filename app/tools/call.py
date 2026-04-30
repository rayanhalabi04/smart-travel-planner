from fastapi import APIRouter, Depends, HTTPException
from typing import Any

from app.tools.registry import get_tool
from app.dependencies import (
    get_ml_model,
    get_feature_columns,
    get_embedder,
)

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.post("/call")
def call_tool(
    request: dict[str, Any],
    model: Any = Depends(get_ml_model),
    feature_columns: list[str] = Depends(get_feature_columns),
    embedder: Any = Depends(get_embedder),
):
    tool_name = request.get("tool_name")
    arguments = request.get("arguments", {})

    tool = get_tool(tool_name)

    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    try:
        result = tool(
            arguments=arguments,
            model=model,
            feature_columns=feature_columns,
            embedder=embedder,   # ✅ ADD THIS
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "tool_name": tool_name,
        "result": result,
    }