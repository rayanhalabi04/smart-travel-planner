from typing import Any

import pandas as pd


def predict_travel_style(
    input_data: dict[str, Any],
    model: Any,
    feature_columns: list[str],
) -> dict[str, Any]:
    """
    Build the input DataFrame in the exact column order used during training,
    then run the ML model prediction.
    """

    input_df = pd.DataFrame([input_data])

    # Ensure all expected columns exist
    for column in feature_columns:
        if column not in input_df.columns:
            input_df[column] = 0

    # Keep only training columns and preserve order
    input_df = input_df[feature_columns]

    prediction = model.predict(input_df)[0]

    result = {
        "predicted_style": prediction,
    }


    return result