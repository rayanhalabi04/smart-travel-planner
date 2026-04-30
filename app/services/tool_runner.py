import inspect
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ToolLog
from app.tools.registry import get_tool


@dataclass
class ToolRuntimeContext:
    model: Any = None
    feature_columns: list[str] | None = None
    embedder: Any = None
    http_client: Any = None
    session: AsyncSession | None = None


def _validation_message(exc: ValidationError) -> str:
    errors = exc.errors(include_url=False)
    return f"Input validation failed: {errors}"


async def _persist_tool_log(
    *,
    session: AsyncSession | None,
    agent_run_id: int | None,
    result: dict[str, Any],
) -> None:
    if session is None or agent_run_id is None:
        return

    tool_log = ToolLog(
        run_id=agent_run_id,
        tool_name=result["tool_name"],
        tool_input=result.get("tool_input"),
        tool_output=result.get("tool_output"),
        status=result["status"],
        error_message=result.get("error_message"),
    )

    session.add(tool_log)
    await session.commit()


async def record_tool_failure(
    *,
    tool_name: str,
    raw_args: dict[str, Any],
    error_message: str,
    context: ToolRuntimeContext,
    agent_run_id: int | None = None,
) -> dict[str, Any]:
    result = {
        "tool_name": tool_name,
        "tool_input": raw_args,
        "tool_output": None,
        "status": "failed",
        "error_message": error_message,
    }

    await _persist_tool_log(
        session=context.session,
        agent_run_id=agent_run_id,
        result=result,
    )

    return result


async def run_tool(
    *,
    tool_name: str,
    raw_args: dict[str, Any],
    context: ToolRuntimeContext,
    agent_run_id: int | None = None,
) -> dict[str, Any]:
    tool_definition = get_tool(tool_name)

    if tool_definition is None:
        return await record_tool_failure(
            tool_name=tool_name,
            raw_args=raw_args,
            error_message=f"Tool '{tool_name}' is not allowed.",
            context=context,
            agent_run_id=agent_run_id,
        )

    try:
        payload = tool_definition.input_schema.model_validate(raw_args)
    except ValidationError as exc:
        return await record_tool_failure(
            tool_name=tool_name,
            raw_args=raw_args,
            error_message=_validation_message(exc),
            context=context,
            agent_run_id=agent_run_id,
        )

    try:
        tool_output = tool_definition.function(
            payload=payload,
            model=context.model,
            feature_columns=context.feature_columns,
            embedder=context.embedder,
            http_client=context.http_client,
            session=context.session,
        )
        if inspect.isawaitable(tool_output):
            tool_output = await tool_output

        result = {
            "tool_name": tool_name,
            "tool_input": payload.model_dump(),
            "tool_output": tool_output,
            "status": "success",
            "error_message": None,
        }
    except Exception as exc:
        result = {
            "tool_name": tool_name,
            "tool_input": payload.model_dump(),
            "tool_output": None,
            "status": "failed",
            "error_message": f"{exc.__class__.__name__}: {exc}",
        }

    await _persist_tool_log(
        session=context.session,
        agent_run_id=agent_run_id,
        result=result,
    )

    return result
