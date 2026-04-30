from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentRun, ToolLog, User
from app.dependencies import get_current_user, get_db_session
from app.schemas.agent import AgentRunRequest, AgentRunResponse, ToolLogResponse
from app.tools.weather_tool import WeatherToolInput, weather_tool

router = APIRouter(prefix="/agent", tags=["agent"])


def extract_city_from_text(text: str) -> str | None:
    known_cities = [
        "Rome",
        "Paris",
        "London",
        "Barcelona",
        "Dubai",
        "Istanbul",
        "Athens",
        "Cairo",
        "Beirut",
        "Tripoli",
    ]

    text_lower = text.lower()

    for city in known_cities:
        if city.lower() in text_lower:
            return city

    return None


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    payload: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AgentRunResponse:
    weather = None
    city = extract_city_from_text(payload.input_text)

    if city:
        try:
            weather_output = await weather_tool(WeatherToolInput(city=city))
            weather = weather_output.result

            temperature = weather.temperature_c

            if temperature < 10:
                weather_comment = "It might be quite cold, so pack warm clothes."
            elif temperature < 20:
                weather_comment = "The weather is mild, good for walking and sightseeing."
            elif temperature < 30:
                weather_comment = "The weather is pleasant and ideal for outdoor activities."
            else:
                weather_comment = "It might be quite hot, so plan indoor or beach activities."

            output_text = (
                f"{city} is a great travel destination. "
                f"Right now, the temperature is {temperature}°C "
                f"with wind speed around {weather.wind_speed_kmh} km/h. "
                f"{weather_comment} "
                f"This makes it a nice option for your trip depending on your preferences."
            )

        except Exception:
            output_text = (
                f"You asked about {city}, but I could not fetch live weather right now. "
                f"I still saved your travel request."
            )
    else:
        output_text = (
            f"I saved your travel request: '{payload.input_text}'. "
            f"Next, I need a destination city so I can check live weather."
        )

    agent_run = AgentRun(
        user_id=current_user.id,
        user_query=payload.input_text,
        final_answer=output_text,
    )

    session.add(agent_run)
    await session.commit()
    await session.refresh(agent_run)

    if city and weather:
        tool_log = ToolLog(
            run_id=agent_run.id,
            tool_name="weather",
            tool_input={"city": city},
            tool_output={
                "city": weather.city,
                "latitude": weather.latitude,
                "longitude": weather.longitude,
                "temperature_c": weather.temperature_c,
                "wind_speed_kmh": weather.wind_speed_kmh,
                "weather_code": weather.weather_code,
                "source": weather.source,
            },
            status="success",
        )

        session.add(tool_log)
        await session.commit()

    return AgentRunResponse(
        id=agent_run.id,
        input_text=agent_run.user_query,
        output_text=agent_run.final_answer,
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
            output_text=run.final_answer,
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