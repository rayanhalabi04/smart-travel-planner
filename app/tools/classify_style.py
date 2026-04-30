from typing import Any

from app.ml.predictor import predict_travel_style
from app.schemas.tools import ClassifyStyleToolInput


TOOL_NAME = "classify_style"


def classify_style_tool(
    payload: ClassifyStyleToolInput,
    model: Any,
    feature_columns: list[str],
    **kwargs: Any,
) -> dict[str, Any]:
    return predict_travel_style(
        input_data=payload.model_dump(),
        model=model,
        feature_columns=feature_columns,
    )
