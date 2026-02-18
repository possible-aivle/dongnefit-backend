"""공시지가 예측 서비스.

학습된 XGBoost 모델을 로드하여 특정 PNU에 대한 10년 예측을 수행.
횡단면/시계열 두 모드 모두 지원.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler
from sqlalchemy.ext.asyncio import AsyncSession
from xgboost import XGBRegressor

from app.crud.prediction import (
    get_buildings_for_pnus,
    get_sgg_growth_rates,
    get_sgg_price_stats,
    get_sgg_transaction_stats,
)
from app.crud.public_data import get_lot_by_pnu
from app.schemas.prediction import (
    ModelMetrics,
    PredictionResponse,
    PriceHistory,
    YearlyPrediction,
)
from app.services.prediction.constants import (
    DEFAULT_ANNUAL_GROWTH_RATE,
    ENHANCED_CROSS_SECTIONAL_FEATURE_NAMES,
    PREDICTION_YEARS,
)
from app.services.prediction.features import (
    build_cross_sectional_vector,
    build_enhanced_cross_sectional_vector,
    build_feature_vector,
)

logger = logging.getLogger(__name__)


class PredictionService:
    """공시지가 예측 서비스 (횡단면/시계열 자동 전환)."""

    def __init__(self) -> None:
        # 시계열 모드
        self.ts_models: dict[int, XGBRegressor] = {}
        # 횡단면 모드
        self.base_model: XGBRegressor | None = None

        self.scaler: StandardScaler | None = None
        self.metadata: dict[str, Any] = {}
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def mode(self) -> str:
        return self.metadata.get("mode", "unknown")

    def load(self, model_dir: str = "./ml_models") -> None:
        """학습된 모델/스케일러/메타데이터 로드."""
        model_path = Path(model_dir)

        metadata_file = model_path / "metadata.json"
        if not metadata_file.exists():
            logger.warning("Model metadata not found at %s. Prediction unavailable.", model_dir)
            return

        self.metadata = json.loads(metadata_file.read_text())

        scaler_file = model_path / "scaler.joblib"
        if not scaler_file.exists():
            logger.warning("Scaler not found at %s", scaler_file)
            return
        self.scaler = joblib.load(scaler_file)

        mode = self.metadata.get("mode", "time_series")

        if mode == "cross_sectional":
            base_file = model_path / "model_base.joblib"
            if base_file.exists():
                self.base_model = joblib.load(base_file)
                self._loaded = True
                logger.info(
                    "ML cross-sectional model loaded, version=%s",
                    self.metadata.get("version", "unknown"),
                )
            else:
                logger.warning("Base model not found at %s", base_file)
        else:
            for k in range(1, PREDICTION_YEARS + 1):
                model_file = model_path / f"model_year_{k}.joblib"
                if model_file.exists():
                    self.ts_models[k] = joblib.load(model_file)

            if self.ts_models:
                self._loaded = True
                logger.info(
                    "ML time-series models loaded: %d models, version=%s",
                    len(self.ts_models),
                    self.metadata.get("version", "unknown"),
                )

    async def predict(self, db: AsyncSession, pnu: str) -> PredictionResponse:
        """특정 PNU에 대한 10년 공시지가 예측."""
        if not self._loaded:
            raise RuntimeError("Prediction models not loaded")

        # 1. 필지 조회
        lot = await get_lot_by_pnu(db, pnu)
        if lot is None:
            raise ValueError(f"필지를 찾을 수 없습니다: {pnu}")

        # 현재 가격: flat 컬럼 우선 → JSONB 폴백
        prices = lot.official_prices or []
        current_price = lot.official_price or 0

        if prices:
            sorted_prices = sorted(prices, key=lambda p: int(p.get("base_year", 0)))
            base_year = int(sorted_prices[-1]["base_year"])
            if current_price <= 0:
                current_price = int(sorted_prices[-1].get("price_per_sqm", 0))
        elif current_price > 0:
            # JSONB 없어도 flat 컬럼만으로 예측 가능
            from datetime import date
            sorted_prices = []
            base_year = date.today().year
        else:
            raise ValueError("공시지가 정보가 없습니다.")

        # 2. 건물 + 통계 조회
        building_map = await get_buildings_for_pnus(db, [pnu])
        building = building_map.get(pnu)

        sgg_code = pnu[:5]
        sgg_stats_map = await get_sgg_transaction_stats(db, [sgg_code])
        sgg_stats = sgg_stats_map.get(sgg_code)

        # 3. 모드별 예측
        mode = self.metadata.get("mode", "time_series")
        is_enhanced = self.metadata.get("enhanced", False)

        if mode == "cross_sectional" and is_enhanced:
            # enhanced 모드: 지역 가격 통계 추가 조회
            sgg_price_stats_map = await get_sgg_price_stats(db, [sgg_code])
            sgg_growth_rates_map = await get_sgg_growth_rates(db, [sgg_code])

            predictions = self._predict_enhanced_cross_sectional(
                lot, base_year, current_price, building, sgg_stats,
                sgg_price_stats_map.get(sgg_code),
                sgg_growth_rates_map.get(sgg_code, DEFAULT_ANNUAL_GROWTH_RATE),
            )
        elif mode == "cross_sectional":
            predictions = self._predict_cross_sectional(
                lot, base_year, current_price, building, sgg_stats
            )
        else:
            predictions = self._predict_timeseries(
                lot, prices, base_year, current_price, building, sgg_stats
            )

        # 4. 가격 이력
        price_history = [
            PriceHistory(
                year=int(p["base_year"]),
                price_per_sqm=int(p.get("price_per_sqm", 0)),
            )
            for p in sorted_prices
        ]

        # 5. 모델 평가 지표
        metrics_data = self.metadata.get("metrics", {})
        avg_metrics = self._compute_avg_metrics(metrics_data)

        return PredictionResponse(
            pnu=pnu,
            current_price_per_sqm=current_price,
            area=lot.area,
            jimok=lot.jimok,
            use_zone=lot.use_zone,
            price_history=price_history,
            predictions=predictions,
            model_version=self.metadata.get("version", "unknown"),
            model_metrics=avg_metrics,
            predicted_at=datetime.now(UTC),
        )

    def _predict_cross_sectional(
        self,
        lot: Any,
        base_year: int,
        current_price: int,
        building: dict[str, Any] | None,
        sgg_stats: dict[str, Any] | None,
    ) -> list[YearlyPrediction]:
        """횡단면 모드: 기본 가격 예측 + 성장률 투영."""
        vec = build_cross_sectional_vector(
            area=lot.area,
            jimok=lot.jimok,
            use_zone=lot.use_zone,
            ownership=lot.ownership,
            owner_count=lot.owner_count,
            base_year=base_year,
            building=building,
            sgg_stats=sgg_stats,
        )

        x_data = np.array([vec], dtype=np.float64)
        x_scaled = self.scaler.transform(x_data)

        model_estimate = float(self.base_model.predict(x_scaled)[0])
        model_estimate = max(model_estimate, 1.0)

        price_ratio = current_price / model_estimate if model_estimate > 0 else 1.0

        # 지역별 성장률 (metadata에 있으면 사용, 없으면 전역 기본값)
        sgg_code = lot.pnu[:5]
        metadata_rates = self.metadata.get("sgg_growth_rates", {})
        growth_rate = metadata_rates.get(
            sgg_code, self.metadata.get("annual_growth_rate", 0.03)
        )
        residual_std = self.metadata.get("residual_std", 0.0)
        area = lot.area or 1.0

        predictions: list[YearlyPrediction] = []
        for k in range(1, PREDICTION_YEARS + 1):
            # 모델 추정 기반 성장 + 필지 보정
            projected = model_estimate * ((1 + growth_rate) ** k) * price_ratio
            projected = max(projected, 0)

            margin = 1.645 * residual_std * math.sqrt(k)

            pred_int = int(round(projected))
            total = int(round(projected * area))
            lower = max(0, int(round(projected - margin)))
            upper = int(round(projected + margin))

            change_pct = (
                ((projected - current_price) / current_price * 100)
                if current_price > 0
                else 0.0
            )

            predictions.append(
                YearlyPrediction(
                    year=base_year + k,
                    year_offset=k,
                    predicted_price_per_sqm=pred_int,
                    predicted_total_price=total,
                    confidence_lower=lower,
                    confidence_upper=upper,
                    change_from_current_pct=round(change_pct, 2),
                )
            )
        return predictions

    def _predict_enhanced_cross_sectional(
        self,
        lot: Any,
        base_year: int,
        current_price: int,
        building: dict[str, Any] | None,
        sgg_stats: dict[str, Any] | None,
        sgg_price_stats: dict[str, float] | None,
        sgg_growth_rate: float,
    ) -> list[YearlyPrediction]:
        """강화 횡단면 모드: 지역별 성장률 적용."""
        vec = build_enhanced_cross_sectional_vector(
            area=lot.area,
            jimok=lot.jimok,
            use_zone=lot.use_zone,
            ownership=lot.ownership,
            owner_count=lot.owner_count,
            base_year=base_year,
            building=building,
            sgg_stats=sgg_stats,
            current_price=current_price,
            sgg_price_stats=sgg_price_stats,
            sgg_growth_rate=sgg_growth_rate,
        )

        x_data = np.array([vec], dtype=np.float64)
        x_scaled = self.scaler.transform(x_data)

        model_estimate = float(self.base_model.predict(x_scaled)[0])
        model_estimate = max(model_estimate, 1.0)

        price_ratio = current_price / model_estimate if model_estimate > 0 else 1.0

        # metadata에 저장된 해당 지역 성장률 우선 사용
        sgg_code = lot.pnu[:5]
        metadata_rates = self.metadata.get("sgg_growth_rates", {})
        growth_rate = metadata_rates.get(sgg_code, sgg_growth_rate)

        residual_std = self.metadata.get("residual_std", 0.0)
        area = lot.area or 1.0

        predictions: list[YearlyPrediction] = []
        for k in range(1, PREDICTION_YEARS + 1):
            projected = model_estimate * ((1 + growth_rate) ** k) * price_ratio
            projected = max(projected, 0)

            margin = 1.645 * residual_std * math.sqrt(k)

            pred_int = int(round(projected))
            total = int(round(projected * area))
            lower = max(0, int(round(projected - margin)))
            upper = int(round(projected + margin))

            change_pct = (
                ((projected - current_price) / current_price * 100)
                if current_price > 0
                else 0.0
            )

            predictions.append(
                YearlyPrediction(
                    year=base_year + k,
                    year_offset=k,
                    predicted_price_per_sqm=pred_int,
                    predicted_total_price=total,
                    confidence_lower=lower,
                    confidence_upper=upper,
                    change_from_current_pct=round(change_pct, 2),
                )
            )
        return predictions

    def _predict_timeseries(
        self,
        lot: Any,
        prices: list[dict[str, Any]],
        base_year: int,
        current_price: int,
        building: dict[str, Any] | None,
        sgg_stats: dict[str, Any] | None,
    ) -> list[YearlyPrediction]:
        """시계열 모드: Direct Multi-step 10개 모델 예측."""
        vec = build_feature_vector(
            area=lot.area,
            jimok=lot.jimok,
            use_zone=lot.use_zone,
            ownership=lot.ownership,
            owner_count=lot.owner_count,
            prices=prices,
            base_year=base_year,
            building=building,
            sgg_stats=sgg_stats,
        )

        x_data = np.array([vec], dtype=np.float64)
        x_scaled = self.scaler.transform(x_data)

        residual_stds = self.metadata.get("residual_stds", {})
        area = lot.area or 1.0

        predictions: list[YearlyPrediction] = []
        for k in range(1, PREDICTION_YEARS + 1):
            model = self.ts_models.get(k)
            if model is None:
                continue

            pred_price = float(model.predict(x_scaled)[0])
            pred_price = max(pred_price, 0)

            res_std = residual_stds.get(str(k), 0.0)
            margin = 1.645 * res_std * math.sqrt(k)

            pred_int = int(round(pred_price))
            total = int(round(pred_price * area))
            lower = max(0, int(round(pred_price - margin)))
            upper = int(round(pred_price + margin))

            change_pct = (
                ((pred_price - current_price) / current_price * 100)
                if current_price > 0
                else 0.0
            )

            predictions.append(
                YearlyPrediction(
                    year=base_year + k,
                    year_offset=k,
                    predicted_price_per_sqm=pred_int,
                    predicted_total_price=total,
                    confidence_lower=lower,
                    confidence_upper=upper,
                    change_from_current_pct=round(change_pct, 2),
                )
            )
        return predictions

    @staticmethod
    def _compute_avg_metrics(
        metrics_data: dict[str, dict[str, float]],
    ) -> ModelMetrics | None:
        if not metrics_data:
            return None
        values = list(metrics_data.values())
        return ModelMetrics(
            rmse=sum(m["rmse"] for m in values) / len(values),
            mae=sum(m["mae"] for m in values) / len(values),
            r2=sum(m["r2"] for m in values) / len(values),
            mape=sum(m["mape"] for m in values) / len(values),
        )
