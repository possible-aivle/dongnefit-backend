"""공시지가 예측 요청/응답 스키마."""

from datetime import datetime

from app.schemas.base import BaseSchema


class PriceHistory(BaseSchema):
    """연도별 공시지가 이력."""

    year: int
    price_per_sqm: int


class YearlyPrediction(BaseSchema):
    """연도별 예측 결과."""

    year: int
    year_offset: int
    predicted_price_per_sqm: int
    predicted_total_price: int
    confidence_lower: int
    confidence_upper: int
    change_from_current_pct: float


class ModelMetrics(BaseSchema):
    """모델 평가 지표."""

    rmse: float
    mae: float
    r2: float
    mape: float


class PredictionResponse(BaseSchema):
    """예측 API 응답."""

    pnu: str
    current_price_per_sqm: int | None
    area: float | None
    jimok: str | None
    use_zone: str | None
    price_history: list[PriceHistory]
    predictions: list[YearlyPrediction]
    model_version: str
    model_metrics: ModelMetrics | None
    predicted_at: datetime
