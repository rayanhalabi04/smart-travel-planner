import asyncio

from app.config import Settings
from app.llm.gemini_client import GeminiLLMClient


def test_gemini_missing_key_fallback_is_safe():
    settings = Settings(
        _env_file=None,
        gemini_api_key=None,
        cheap_model="gemini-2.5-flash-lite",
        strong_model="gemini-2.5-flash",
    )
    client = GeminiLLMClient(settings=settings)

    fallback_extraction = {
        "destination_city": "Paris",
        "travel_style": "Cultural",
        "interests": ["culture", "museum"],
        "rag_query": "Cultural",
        "numeric_features": {},
        "notes": None,
    }

    extracted, extraction_usage = asyncio.run(
        client.cheap_extract_and_rewrite(
            user_query="I want museums in Paris",
            fallback=fallback_extraction,
        )
    )
    assert extracted == fallback_extraction
    assert extraction_usage["step_name"] == "cheap_extraction"

    answer, synthesis_usage = asyncio.run(
        client.strong_synthesize(
            user_query="I want museums in Paris",
            extracted_preferences={},
            destination_result=None,
            classifier_result=None,
            weather_result=None,
            tool_results=[],
            fallback_answer="Fallback answer.",
        )
    )
    assert answer == "Fallback answer."
    assert synthesis_usage["step_name"] == "strong_synthesis"
