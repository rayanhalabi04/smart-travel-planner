import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.llm.costs import summarize_step_costs
from app.llm.gemini_client import GeminiLLMClient
from app.services.tool_runner import ToolRuntimeContext, record_tool_failure, run_tool
from app.utils.travel_style import normalize_travel_style


CLASSIFIER_FIELDS = [
    "avg_daily_cost_usd",
    "avg_hotel_price_usd",
    "tourism_density",
    "hiking_trails",
    "water_sports",
    "beach_quality",
    "historical_sites",
    "museums_galleries",
    "family_friendly_score",
    "luxury_resorts",
    "avg_temp_summer_c",
]


KNOWN_CITIES = [
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


STYLE_TO_PREFERENCE_KEY = {
    "budget": "budget",
    "luxury": "luxury",
    "family": "family",
    "adventure": "hiking",
    "relaxation": "beach",
    "culture": "culture",
    "beach": "beach",
    "cultural": "culture",
}

INTEREST_ALIASES = {
    "budget": "budget",
    "affordable": "budget",
    "luxury": "luxury",
    "family": "family",
    "kids": "family",
    "children": "family",
    "hiking": "hiking",
    "trail": "hiking",
    "mountain": "hiking",
    "beach": "beach",
    "water sports": "water_sports",
    "watersports": "water_sports",
    "surf": "water_sports",
    "diving": "water_sports",
    "snorkeling": "water_sports",
    "culture": "culture",
    "historical": "culture",
    "history": "culture",
    "museum": "culture",
    "art": "culture",
}


class TravelAgentState(TypedDict, total=False):
    user_query: str
    rag_top_k: int
    runtime: ToolRuntimeContext
    agent_run_id: int
    llm_client: GeminiLLMClient
    destination_city: str | None
    extracted_preferences: dict[str, Any]
    numeric_features: dict[str, float]
    llm_usage_steps: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    destination_result: dict[str, Any] | None
    classifier_result: dict[str, Any] | None
    weather_result: dict[str, Any] | None
    final_answer: str


@dataclass
class TravelAgentResult:
    final_answer: str
    tool_results: list[dict[str, Any]]
    token_usage: dict[str, Any] | None = None
    cost_usd: float | None = None


def _extract_city_from_text(text: str) -> str | None:
    lowered = text.lower()
    for city in KNOWN_CITIES:
        if city.lower() in lowered:
            return city

    pattern = re.compile(
        r"\b(?:in|to|visit|travel to|going to)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)"
    )
    match = pattern.search(text)
    if match:
        return match.group(1).strip()

    return None


def _extract_preference_tokens(text: str) -> dict[str, bool]:
    lowered = text.lower()
    return {
        "budget": any(token in lowered for token in ["budget", "cheap", "affordable", "backpack"]),
        "luxury": any(token in lowered for token in ["luxury", "resort", "premium", "five-star", "5-star"]),
        "family": any(token in lowered for token in ["family", "kids", "children"]),
        "hiking": any(token in lowered for token in ["hiking", "trail", "mountain", "trek"]),
        "beach": any(token in lowered for token in ["beach", "coast", "island", "swim"]),
        "water_sports": any(token in lowered for token in ["surf", "diving", "snorkel", "kayak"]),
        "culture": any(token in lowered for token in ["museum", "history", "historical", "culture", "art"]),
    }


def _infer_travel_style(preferences: dict[str, bool]) -> str | None:
    if preferences["luxury"]:
        return "Luxury"
    if preferences["budget"]:
        return "Budget"
    if preferences["family"]:
        return "Family"
    if preferences["hiking"]:
        return "Adventure"
    if preferences["beach"] or preferences["water_sports"]:
        return "Relaxation"
    if preferences["culture"]:
        return "Culture"
    return None


def _extract_numeric_features(text: str) -> dict[str, float]:
    extracted: dict[str, float] = {}
    lowered = text.lower()
    aliases = {
        "avg_daily_cost_usd": ["avg_daily_cost_usd", "daily_cost", "daily budget", "budget per day"],
        "avg_hotel_price_usd": ["avg_hotel_price_usd", "hotel_price", "hotel budget"],
        "tourism_density": ["tourism_density"],
        "hiking_trails": ["hiking_trails"],
        "water_sports": ["water_sports"],
        "beach_quality": ["beach_quality"],
        "historical_sites": ["historical_sites"],
        "museums_galleries": ["museums_galleries"],
        "family_friendly_score": ["family_friendly_score"],
        "luxury_resorts": ["luxury_resorts"],
        "avg_temp_summer_c": ["avg_temp_summer_c", "summer_temp_c"],
    }

    for field, field_aliases in aliases.items():
        for alias in field_aliases:
            pattern = re.compile(rf"{re.escape(alias)}\s*[:=]?\s*(-?\d+(?:\.\d+)?)")
            match = pattern.search(lowered)
            if match:
                extracted[field] = float(match.group(1))
                break

    return extracted


def _deterministic_extraction(user_query: str) -> dict[str, Any]:
    preferences = _extract_preference_tokens(user_query)
    travel_style_hint = _infer_travel_style(preferences)
    destination_city = _extract_city_from_text(user_query)
    extracted_numeric = _extract_numeric_features(user_query)

    complete_numeric_features = {
        field: extracted_numeric[field]
        for field in CLASSIFIER_FIELDS
        if field in extracted_numeric
    }

    interests = [
        name.replace("_", " ")
        for name, is_active in preferences.items()
        if is_active
    ]

    return {
        "destination_city": destination_city,
        "travel_style": travel_style_hint,
        "interests": interests,
        "rag_query": travel_style_hint or user_query,
        "numeric_features": complete_numeric_features,
        "notes": None,
    }


def _normalized_preference_key(label: str) -> str | None:
    key = label.strip().lower().replace("_", " ")
    return INTEREST_ALIASES.get(key)


def _preferences_from_extraction(
    *,
    user_query: str,
    extraction: dict[str, Any],
) -> tuple[dict[str, bool], str | None, list[str]]:
    preferences = _extract_preference_tokens(user_query)

    interests = extraction.get("interests")
    if isinstance(interests, list):
        for interest in interests:
            if not isinstance(interest, str):
                continue
            pref_key = _normalized_preference_key(interest)
            if pref_key and pref_key in preferences:
                preferences[pref_key] = True

    raw_travel_style = extraction.get("travel_style")
    travel_style_hint = normalize_travel_style(raw_travel_style)
    if travel_style_hint:
        style_key = STYLE_TO_PREFERENCE_KEY.get(travel_style_hint.lower())
        if style_key and style_key in preferences:
            preferences[style_key] = True
    else:
        travel_style_hint = normalize_travel_style(_infer_travel_style(preferences))

    normalized_interests = [
        key.replace("_", " ") for key, value in preferences.items() if value
    ]

    return preferences, travel_style_hint, normalized_interests


def _tool_results_with_new(
    state: TravelAgentState,
    tool_result: dict[str, Any],
) -> list[dict[str, Any]]:
    current = list(state.get("tool_results", []))
    current.append(tool_result)
    return current


def _llm_usage_with_new(
    state: TravelAgentState,
    usage: dict[str, Any],
) -> list[dict[str, Any]]:
    current = list(state.get("llm_usage_steps", []))
    current.append(usage)
    return current


async def _extract_preferences_node(state: TravelAgentState) -> TravelAgentState:
    user_query = state["user_query"]
    fallback_extraction = _deterministic_extraction(user_query)

    extraction, extraction_usage = await state["llm_client"].cheap_extract_and_rewrite(
        user_query=user_query,
        fallback=fallback_extraction,
    )

    preferences, travel_style_hint, normalized_interests = _preferences_from_extraction(
        user_query=user_query,
        extraction=extraction,
    )

    destination_city = extraction.get("destination_city") or fallback_extraction.get(
        "destination_city"
    )

    numeric_features_raw = extraction.get("numeric_features", {})
    complete_numeric_features = {
        field: float(numeric_features_raw[field])
        for field in CLASSIFIER_FIELDS
        if field in numeric_features_raw
    }

    rag_query = extraction.get("rag_query")
    if not isinstance(rag_query, str) or not rag_query.strip():
        rag_query = fallback_extraction["rag_query"]

    return {
        "destination_city": destination_city,
        "extracted_preferences": {
            "preferences": preferences,
            "travel_style_hint": travel_style_hint,
            "interests": normalized_interests,
            "rag_query": rag_query,
            "notes": extraction.get("notes"),
        },
        "numeric_features": complete_numeric_features,
        "llm_usage_steps": _llm_usage_with_new(state, extraction_usage),
    }


async def _destination_search_node(state: TravelAgentState) -> TravelAgentState:
    preferences = state.get("extracted_preferences", {})
    style_hint = normalize_travel_style(preferences.get("travel_style_hint"))
    rag_query = preferences.get("rag_query") or state["user_query"]

    raw_args: dict[str, Any] = {
        "query": rag_query,
        "top_k": state.get("rag_top_k", 5),
        "travel_style": style_hint,
    }

    tool_result = await run_tool(
        tool_name="destination_search",
        raw_args=raw_args,
        context=state["runtime"],
        agent_run_id=state["agent_run_id"],
    )

    return {
        "tool_results": _tool_results_with_new(state, tool_result),
        "destination_result": tool_result,
    }


async def _classify_style_node(state: TravelAgentState) -> TravelAgentState:
    numeric_features = state.get("numeric_features", {})

    if any(field not in numeric_features for field in CLASSIFIER_FIELDS):
        tool_result = await record_tool_failure(
            tool_name="classify_style",
            raw_args=numeric_features,
            error_message=(
                "Classifier skipped: missing one or more required numeric features in user input."
            ),
            context=state["runtime"],
            agent_run_id=state["agent_run_id"],
        )
    else:
        tool_result = await run_tool(
            tool_name="classify_style",
            raw_args=numeric_features,
            context=state["runtime"],
            agent_run_id=state["agent_run_id"],
        )

    return {
        "tool_results": _tool_results_with_new(state, tool_result),
        "classifier_result": tool_result,
    }


async def _weather_node(state: TravelAgentState) -> TravelAgentState:
    city = state.get("destination_city")

    if not city:
        tool_result = await record_tool_failure(
            tool_name="weather",
            raw_args={},
            error_message="Weather skipped: no destination city was detected in the user query.",
            context=state["runtime"],
            agent_run_id=state["agent_run_id"],
        )
    else:
        tool_result = await run_tool(
            tool_name="weather",
            raw_args={"city": city},
            context=state["runtime"],
            agent_run_id=state["agent_run_id"],
        )

    return {
        "tool_results": _tool_results_with_new(state, tool_result),
        "weather_result": tool_result,
    }


def _weather_context_line(weather_output: dict[str, Any] | None) -> tuple[str, str | None]:
    if not weather_output:
        return "", None

    result = weather_output.get("result", {})
    city = result.get("city")
    temperature = result.get("temperature_c")
    wind_speed = result.get("wind_speed_kmh")
    weather_code = result.get("weather_code")

    weather_line = (
        f"Live conditions in {city}: {temperature}°C and wind around {wind_speed} km/h "
        f"(weather code {weather_code})."
    )

    tension = None
    if temperature is not None and float(temperature) < 8:
        tension = "Outdoor-heavy plans may feel cold right now."
    elif temperature is not None and float(temperature) > 32:
        tension = "Outdoor peak-hour plans may feel very hot right now."
    elif weather_code is not None and int(weather_code) >= 50:
        tension = "There may be precipitation, so outdoor plans need a backup option."

    return weather_line, tension


def _deterministic_synthesis(state: TravelAgentState) -> str:
    destination_result = state.get("destination_result")
    classifier_result = state.get("classifier_result")
    weather_result = state.get("weather_result")
    preferences = state.get("extracted_preferences", {}).get("preferences", {})

    lines: list[str] = []

    if destination_result and destination_result.get("status") == "success":
        output = destination_result.get("tool_output", {})
        destinations = output.get("destinations", [])
        matches = output.get("matches", [])

        if destinations:
            top_names = ", ".join(
                f"{item['destination_name']} ({item['country']})"
                for item in destinations[:3]
            )
            lines.append(f"Top destination candidates: {top_names}.")
        else:
            lines.append("I could not find strong destination matches from the knowledge base.")

        if matches:
            evidence_bits = []
            for item in matches[:2]:
                snippet = item.get("snippet", "")
                destination_name = item.get("destination_name")
                evidence_bits.append(f"{destination_name}: \"{snippet}\"")
            lines.append("Knowledge evidence: " + " | ".join(evidence_bits))
    else:
        destination_error = destination_result.get("error_message") if destination_result else None
        lines.append(
            "Destination retrieval was unavailable"
            + (f" ({destination_error})." if destination_error else ".")
        )

    if classifier_result and classifier_result.get("status") == "success":
        predicted_style = classifier_result.get("tool_output", {}).get("predicted_style")
        lines.append(f"Model-based style classification: {predicted_style}.")
    else:
        classifier_error = classifier_result.get("error_message") if classifier_result else None
        if classifier_error:
            lines.append(f"Style classifier note: {classifier_error}")

    if any(preferences.values()):
        active_preferences = [
            preference_name.replace("_", " ")
            for preference_name, is_active in preferences.items()
            if is_active
        ]
        lines.append("Detected interests: " + ", ".join(active_preferences) + ".")

    weather_output = (
        weather_result.get("tool_output")
        if weather_result and weather_result.get("status") == "success"
        else None
    )
    weather_line, weather_tension = _weather_context_line(weather_output)
    if weather_line:
        lines.append(weather_line)
    if weather_tension:
        lines.append(f"Planning caution: {weather_tension}")
    elif weather_result and weather_result.get("status") != "success":
        weather_error = weather_result.get("error_message")
        lines.append(f"Weather note: {weather_error}")

    lines.append(
        "Recommendation synthesis: pick one of the top destination matches that aligns with your interests and current conditions, and keep a weather-aware backup activity."
    )

    return " ".join(lines)


async def _synthesis_node(state: TravelAgentState) -> TravelAgentState:
    fallback_answer = _deterministic_synthesis(state)

    final_answer, synthesis_usage = await state["llm_client"].strong_synthesize(
        user_query=state["user_query"],
        extracted_preferences=state.get("extracted_preferences", {}),
        destination_result=state.get("destination_result"),
        classifier_result=state.get("classifier_result"),
        weather_result=state.get("weather_result"),
        tool_results=state.get("tool_results", []),
        fallback_answer=fallback_answer,
    )

    return {
        "final_answer": final_answer,
        "llm_usage_steps": _llm_usage_with_new(state, synthesis_usage),
    }


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(TravelAgentState)
    graph.add_node("extract_preferences", _extract_preferences_node)
    graph.add_node("destination_search", _destination_search_node)
    graph.add_node("classify_style", _classify_style_node)
    graph.add_node("weather", _weather_node)
    graph.add_node("synthesize", _synthesis_node)

    graph.set_entry_point("extract_preferences")
    graph.add_edge("extract_preferences", "destination_search")
    graph.add_edge("destination_search", "classify_style")
    graph.add_edge("classify_style", "weather")
    graph.add_edge("weather", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()


def _build_tracing_config(agent_run_id: int | None) -> dict[str, Any] | None:
    tracing_enabled = (
        os.getenv("LANGSMITH_TRACING", "").lower() == "true"
        or os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
    )
    if not tracing_enabled:
        return None

    return {
        "run_name": "travel_agent_two_models",
        "tags": ["smart-travel-planner", "assignment-two-models"],
        "metadata": {"agent_run_id": agent_run_id},
    }


async def run_travel_agent(
    *,
    user_query: str,
    session: AsyncSession,
    model: Any,
    feature_columns: list[str],
    embedder: Any,
    settings: Settings,
    agent_run_id: int,
) -> TravelAgentResult:
    runtime = ToolRuntimeContext(
        model=model,
        feature_columns=feature_columns,
        embedder=embedder,
        http_client=None,
        session=session,
    )
    graph = _build_graph()
    initial_state: TravelAgentState = {
        "user_query": user_query,
        "rag_top_k": max(1, min(10, settings.rag_top_k)),
        "runtime": runtime,
        "agent_run_id": agent_run_id,
        "llm_client": GeminiLLMClient(settings=settings),
        "llm_usage_steps": [],
        "tool_results": [],
    }

    # LangSmith/LangChain tracing is optional and controlled via env vars.
    trace_config = _build_tracing_config(agent_run_id=agent_run_id)
    if trace_config:
        final_state = await graph.ainvoke(initial_state, config=trace_config)
    else:
        final_state = await graph.ainvoke(initial_state)

    step_costs = final_state.get("llm_usage_steps", [])
    summary = summarize_step_costs(step_costs)

    step_map = {item.get("step_name"): item for item in step_costs}
    token_usage = {
        "cheap_extraction": step_map.get("cheap_extraction"),
        "strong_synthesis": step_map.get("strong_synthesis"),
        "steps": step_costs,
        "total_input_tokens": summary["total_input_tokens"],
        "total_output_tokens": summary["total_output_tokens"],
        "total_tokens": summary["total_tokens"],
        "total_estimated_cost_usd": summary["estimated_cost_usd"],
        "estimated": summary["estimated"],
    }

    return TravelAgentResult(
        final_answer=final_state.get(
            "final_answer",
            "I could not complete the travel analysis. Please try again with more details.",
        ),
        tool_results=final_state.get("tool_results", []),
        token_usage=token_usage,
        cost_usd=summary["estimated_cost_usd"],
    )
