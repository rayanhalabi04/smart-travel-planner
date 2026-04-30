from typing import Any

from app.ml.predictor import predict_travel_style


TOOL_NAME = "classify_style"


def classify_style_tool(
    arguments: dict[str, Any],
    model: Any,
    feature_columns: list[str],
    **kwargs: Any,
) -> dict[str, Any]:
    return predict_travel_style(
        input_data=arguments,
        model=model,
        feature_columns=feature_columns,
    )