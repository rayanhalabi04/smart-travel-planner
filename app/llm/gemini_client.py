import asyncio
import json
import re
from typing import Any

from app.config import Settings
from app.llm.costs import build_step_cost

try:
    from google import genai as google_genai
except Exception:  # pragma: no cover - optional dependency at runtime
    google_genai = None


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


def _strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _extract_json_dict(text: str) -> dict[str, Any] | None:
    cleaned = _strip_json_fences(text)

    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        payload = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def _normalize_interest_list(raw_interests: Any) -> list[str]:
    if not isinstance(raw_interests, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()

    for value in raw_interests:
        if not isinstance(value, str):
            continue

        item = value.strip()
        if not item:
            continue

        item_key = item.lower()
        if item_key in seen:
            continue
        seen.add(item_key)
        normalized.append(item)

    return normalized


def _normalize_numeric_features(raw_features: Any) -> dict[str, float]:
    if not isinstance(raw_features, dict):
        return {}

    normalized: dict[str, float] = {}
    for key in CLASSIFIER_FIELDS:
        if key not in raw_features:
            continue
        try:
            normalized[key] = float(raw_features[key])
        except (TypeError, ValueError):
            continue

    return normalized


class GeminiLLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: Any = None

        if not settings.gemini_api_key:
            return

        if google_genai is None:
            return

        try:
            self._client = google_genai.Client(api_key=settings.gemini_api_key)
        except Exception:
            self._client = None

    async def cheap_extract_and_rewrite(
        self,
        *,
        user_query: str,
        fallback: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        model_name = self.settings.resolved_cheap_model
        prompt = (
            "Extract travel preferences from the user query and return ONLY valid JSON with this exact schema:\n"
            "{\n"
            '  "destination_city": string|null,\n'
            '  "travel_style": string|null,\n'
            '  "interests": string[],\n'
            '  "rag_query": string,\n'
            '  "numeric_features": {'
            + ", ".join(f'"{field}": number' for field in CLASSIFIER_FIELDS)
            + "},\n"
            '  "notes": string|null\n'
            "}\n"
            "Rules:\n"
            "- Use null when unknown.\n"
            "- Keep interests concise.\n"
            "- Only include numeric_features explicitly present in user text.\n"
            "- rag_query should be a concise retrieval query.\n"
            "- Do not include markdown.\n\n"
            f"User query:\n{user_query}"
        )

        if self._client is None:
            usage = build_step_cost(
                step_name="cheap_extraction",
                model_name=model_name,
                input_text=prompt,
                output_text=json.dumps(fallback),
                usage_metadata=None,
            )
            return fallback, usage

        response_text, usage_metadata = await self._generate_content(
            model_name=model_name,
            prompt=prompt,
            response_mime_type="application/json",
        )

        payload = _extract_json_dict(response_text or "")
        if payload is None:
            usage = build_step_cost(
                step_name="cheap_extraction",
                model_name=model_name,
                input_text=prompt,
                output_text=json.dumps(fallback),
                usage_metadata=usage_metadata,
            )
            return fallback, usage

        extracted = self._normalize_extraction(payload=payload, fallback=fallback)
        usage = build_step_cost(
            step_name="cheap_extraction",
            model_name=model_name,
            input_text=prompt,
            output_text=json.dumps(extracted),
            usage_metadata=usage_metadata,
        )
        return extracted, usage

    async def strong_synthesize(
        self,
        *,
        user_query: str,
        extracted_preferences: dict[str, Any],
        destination_result: dict[str, Any] | None,
        classifier_result: dict[str, Any] | None,
        weather_result: dict[str, Any] | None,
        tool_results: list[dict[str, Any]],
        fallback_answer: str,
    ) -> tuple[str, dict[str, Any]]:
        model_name = self.settings.resolved_strong_model

        synthesis_input = {
            "user_query": user_query,
            "extracted_preferences": extracted_preferences,
            "destination_search": destination_result,
            "classify_style": classifier_result,
            "weather": weather_result,
            "all_tool_results": tool_results,
        }

        prompt = (
            "You are a travel planning assistant. Create a concise synthesis answer.\n"
            "Requirements:\n"
            "- Recommend destination options.\n"
            "- Reference RAG evidence from destination_search.\n"
            "- Include classifier result when available.\n"
            "- Include weather when available.\n"
            "- Mention conflicts/tensions (e.g., good hiking but rainy weather).\n"
            "- If tools failed/skipped, acknowledge that briefly.\n"
            "- Do not output JSON.\n\n"
            f"Structured context:\n{json.dumps(synthesis_input, ensure_ascii=True)}"
        )

        if self._client is None:
            usage = build_step_cost(
                step_name="strong_synthesis",
                model_name=model_name,
                input_text=prompt,
                output_text=fallback_answer,
                usage_metadata=None,
            )
            return fallback_answer, usage

        response_text, usage_metadata = await self._generate_content(
            model_name=model_name,
            prompt=prompt,
            response_mime_type=None,
        )

        final_answer = (response_text or "").strip() or fallback_answer
        usage = build_step_cost(
            step_name="strong_synthesis",
            model_name=model_name,
            input_text=prompt,
            output_text=final_answer,
            usage_metadata=usage_metadata,
        )
        return final_answer, usage

    async def _generate_content(
        self,
        *,
        model_name: str,
        prompt: str,
        response_mime_type: str | None,
    ) -> tuple[str | None, Any]:
        if self._client is None:
            return None, None

        config: dict[str, Any] = {"temperature": 0}
        if response_mime_type:
            config["response_mime_type"] = response_mime_type

        try:
            aio_models = getattr(getattr(self._client, "aio", None), "models", None)
            if aio_models is not None and hasattr(aio_models, "generate_content"):
                response = await aio_models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
            else:
                response = await asyncio.to_thread(
                    self._client.models.generate_content,
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
        except Exception:
            return None, None

        usage_metadata = getattr(response, "usage_metadata", None)
        response_text = self._response_text(response)
        return response_text, usage_metadata

    def _response_text(self, response: Any) -> str:
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text

        candidates = getattr(response, "candidates", None)
        if not candidates:
            return ""

        parts: list[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            candidate_parts = getattr(content, "parts", None) if content else None
            if not candidate_parts:
                continue

            for part in candidate_parts:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    parts.append(part_text)

        return "\n".join(parts)

    def _normalize_extraction(
        self,
        *,
        payload: dict[str, Any],
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        destination_city = payload.get("destination_city")
        if not isinstance(destination_city, str) or not destination_city.strip():
            destination_city = fallback.get("destination_city")
        else:
            destination_city = destination_city.strip()

        travel_style = payload.get("travel_style")
        if not isinstance(travel_style, str) or not travel_style.strip():
            travel_style = fallback.get("travel_style")
        else:
            travel_style = travel_style.strip()

        interests = _normalize_interest_list(payload.get("interests"))
        if not interests:
            interests = _normalize_interest_list(fallback.get("interests", []))

        rag_query = payload.get("rag_query")
        if not isinstance(rag_query, str) or not rag_query.strip():
            rag_query = str(fallback.get("rag_query", "")).strip()
        else:
            rag_query = rag_query.strip()

        numeric_features = _normalize_numeric_features(payload.get("numeric_features"))
        if not numeric_features:
            numeric_features = _normalize_numeric_features(
                fallback.get("numeric_features", {})
            )

        notes = payload.get("notes")
        if notes is not None and not isinstance(notes, str):
            notes = None

        return {
            "destination_city": destination_city,
            "travel_style": travel_style,
            "interests": interests,
            "rag_query": rag_query,
            "numeric_features": numeric_features,
            "notes": notes,
        }
