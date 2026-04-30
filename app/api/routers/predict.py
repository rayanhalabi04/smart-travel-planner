from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_feature_columns, get_ml_model
from app.ml.predictor import predict_travel_style
from app.schemas.ml import TravelStyleRequest, TravelStyleResponse

router = APIRouter(prefix="/predict", tags=["Prediction"])


@router.post("", response_model=TravelStyleResponse)
def predict(
    input_data: TravelStyleRequest,
    model: Any = Depends(get_ml_model),
    feature_columns: list[str] = Depends(get_feature_columns),
):
    return predict_travel_style(
        input_data=input_data.model_dump(),
        model=model,
        feature_columns=feature_columns,
    )