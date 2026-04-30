from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.travel_agent import run_travel_agent
from app.config import Settings
from app.db.models import AgentRun, ToolLog, User
from app.dependencies import (
    get_app_settings,
    get_current_user,
    get_db_session,
    get_embedder,
    get_feature_columns,
    get_ml_model,
)
from app.schemas.agent import AgentRunRequest, AgentRunResponse, ToolLogResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    payload: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    model: Any = Depends(get_ml_model),
    feature_columns: list[str] = Depends(get_feature_columns),
    embedder: Any = Depends(get_embedder),
    settings: Settings = Depends(get_app_settings),
) -> AgentRunResponse:
    agent_run = AgentRun(
        user_id=current_user.id,
        user_query=payload.input_text,
        final_answer=None,
        status="running",
    )

    session.add(agent_run)
    await session.commit()
    await session.refresh(agent_run)

    try:
        result = await run_travel_agent(
            user_query=payload.input_text,
            session=session,
            model=model,
            feature_columns=feature_columns,
            embedder=embedder,
            settings=settings,
            agent_run_id=agent_run.id,
        )
        agent_run.final_answer = result.final_answer
        agent_run.status = "success"
    except Exception as exc:
        agent_run.final_answer = (
            "I couldn't complete your travel analysis due to an internal error. "
            "Please try again with a more specific request."
        )
        agent_run.status = "failed"

        # Persist an explicit failure log for troubleshooting when the graph fails.
        session.add(
            ToolLog(
                run_id=agent_run.id,
                tool_name="agent_runtime",
                tool_input={"input_text": payload.input_text},
                tool_output=None,
                status="failed",
                error_message=f"{exc.__class__.__name__}: {exc}",
            )
        )

        await session.commit()
    else:
        await session.commit()

    return AgentRunResponse(
        id=agent_run.id,
        input_text=agent_run.user_query,
        output_text=agent_run.final_answer or "",
    )


@router.get("/history", response_model=list[AgentRunResponse])
async def get_agent_history(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[AgentRunResponse]:
    result = await session.execute(
        select(AgentRun)
        .where(AgentRun.user_id == current_user.id)
        .order_by(AgentRun.created_at.desc())
    )

    runs = result.scalars().all()

    return [
        AgentRunResponse(
            id=run.id,
            input_text=run.user_query,
            output_text=run.final_answer or "",
        )
        for run in runs
    ]


# ✅ FIXED ENDPOINT (correct indentation)
@router.get("/runs/{run_id}/tools", response_model=list[ToolLogResponse])
async def get_run_tool_logs(
    run_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ToolLogResponse]:

    run_result = await session.execute(
        select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.user_id == current_user.id,
        )
    )

    run = run_result.scalar_one_or_none()

    if run is None:
        return []

    logs_result = await session.execute(
        select(ToolLog)
        .where(ToolLog.run_id == run_id)
        .order_by(ToolLog.created_at.asc())
    )

    logs = logs_result.scalars().all()

    return [
        ToolLogResponse(
            id=log.id,
            tool_name=log.tool_name,
            tool_input=log.tool_input,
            tool_output=log.tool_output,
            status=log.status,
            error_message=log.error_message,
        )
        for log in logs
    ]
