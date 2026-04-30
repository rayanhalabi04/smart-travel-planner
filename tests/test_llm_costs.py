import pytest

from app.llm.costs import build_step_cost


def test_build_step_cost_uses_usage_metadata_for_known_model():
    result = build_step_cost(
        step_name="cheap_extraction",
        model_name="gemini-2.5-flash-lite",
        input_text="ignored",
        output_text="ignored",
        usage_metadata={
            "prompt_token_count": 1000,
            "candidates_token_count": 500,
            "total_token_count": 1500,
        },
    )

    assert result["input_tokens"] == 1000
    assert result["output_tokens"] == 500
    assert result["total_tokens"] == 1500
    assert result["estimated"] is False
    assert result["estimated_cost_usd"] == pytest.approx(0.0003)


def test_build_step_cost_unknown_model_costs_zero():
    result = build_step_cost(
        step_name="strong_synthesis",
        model_name="some-unknown-model",
        input_text="hello",
        output_text="world",
        usage_metadata=None,
    )

    assert result["estimated_cost_usd"] == 0.0
    assert result["estimated"] is True
