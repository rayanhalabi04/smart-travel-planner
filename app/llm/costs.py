import math
from typing import Any


MODEL_PRICING_USD_PER_MILLION: dict[str, dict[str, float]] = {
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
}


def estimate_tokens_from_text(text: str | None) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _usage_value(usage_metadata: Any, keys: list[str]) -> int | None:
    if usage_metadata is None:
        return None

    for key in keys:
        value = None

        if isinstance(usage_metadata, dict):
            value = usage_metadata.get(key)
        else:
            value = getattr(usage_metadata, key, None)

        if value is None:
            continue

        try:
            return int(value)
        except (TypeError, ValueError):
            continue

    return None


def _normalize_model_name(model_name: str) -> str:
    return model_name.strip().lower()


def build_step_cost(
    *,
    step_name: str,
    model_name: str,
    input_text: str,
    output_text: str,
    usage_metadata: Any = None,
) -> dict[str, Any]:
    input_tokens = _usage_value(
        usage_metadata,
        ["prompt_token_count", "input_token_count", "input_tokens"],
    )
    output_tokens = _usage_value(
        usage_metadata,
        ["candidates_token_count", "output_token_count", "output_tokens"],
    )
    total_tokens = _usage_value(
        usage_metadata,
        ["total_token_count", "total_tokens"],
    )

    estimated = False

    if input_tokens is None:
        input_tokens = estimate_tokens_from_text(input_text)
        estimated = True

    if output_tokens is None:
        output_tokens = estimate_tokens_from_text(output_text)
        estimated = True

    if total_tokens is None:
        total_tokens = input_tokens + output_tokens

    pricing = MODEL_PRICING_USD_PER_MILLION.get(_normalize_model_name(model_name))

    if pricing is None:
        estimated_cost_usd = 0.0
        estimated = True
    else:
        estimated_cost_usd = (
            (input_tokens / 1_000_000.0) * pricing["input"]
            + (output_tokens / 1_000_000.0) * pricing["output"]
        )

    return {
        "step_name": step_name,
        "model_name": model_name,
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "total_tokens": int(total_tokens),
        "estimated_cost_usd": float(estimated_cost_usd),
        "estimated": bool(estimated),
    }


def summarize_step_costs(step_costs: list[dict[str, Any]]) -> dict[str, Any]:
    total_input_tokens = sum(int(item.get("input_tokens", 0)) for item in step_costs)
    total_output_tokens = sum(int(item.get("output_tokens", 0)) for item in step_costs)
    total_tokens = sum(int(item.get("total_tokens", 0)) for item in step_costs)
    total_cost_usd = sum(float(item.get("estimated_cost_usd", 0.0)) for item in step_costs)
    estimated = any(bool(item.get("estimated", True)) for item in step_costs)

    return {
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": float(total_cost_usd),
        "estimated": estimated,
    }
