import inspect
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
async def call_tool(
    request: dict[str, Any],
    model: Any = Depends(get_ml_model),
    feature_columns: list[str] = Depends(get_feature_columns),
    embedder: Any = Depends(get_embedder),
):
    tool_name = request.get("tool_name")
    arguments = request.get("arguments", {})

    tool_definition = get_tool(tool_name)

    if tool_definition is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    try:
        payload = tool_definition.input_schema.model_validate(arguments)
        result = tool_definition.function(
            payload=payload,
            model=model,
            feature_columns=feature_columns,
            embedder=embedder,
        )
        if inspect.isawaitable(result):
            result = await result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "tool_name": tool_name,
        "result": result,
    }
