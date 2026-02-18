"""XGBoost 모델 훈련 파이프라인.

두 가지 훈련 모드를 지원:
1. 시계열 모드 (time_series): 필지별 multi-year 이력이 있을 때
   → Direct Multi-step (year_offset별 10개 모델)
2. 횡단면 모드 (cross_sectional): 필지별 1년 데이터만 있을 때
   → 1개 가격 예측 모델 + 성장률 기반 10년 투영

자동 감지: lots의 평균 이력 연수가 3년 이상이면 시계열, 아니면 횡단면.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import optuna
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from app.services.prediction.constants import (
    CROSS_SECTIONAL_FEATURE_NAMES,
    DEFAULT_ANNUAL_GROWTH_RATE,
    ENHANCED_CROSS_SECTIONAL_FEATURE_NAMES,
    PREDICTION_YEARS,
    TIMESERIES_FEATURE_NAMES,
)
from app.services.prediction.features import (
    build_cross_sectional_vector,
    build_enhanced_cross_sectional_vector,
    build_feature_vector,
)

logger = logging.getLogger(__name__)

optuna.logging.set_verbosity(optuna.logging.WARNING)


# ─────────────────── 공통 유틸 ───────────────────


def _time_split(
    x_data: np.ndarray,
    y: np.ndarray,
    *,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> tuple[
    tuple[np.ndarray, np.ndarray],
    tuple[np.ndarray, np.ndarray],
    tuple[np.ndarray, np.ndarray],
]:
    """시간 기반 분할 (순서 유지)."""
    n = len(x_data)
    test_start = int(n * (1 - test_ratio))
    val_start = int(n * (1 - test_ratio - val_ratio))

    x_train, y_train = x_data[:val_start], y[:val_start]
    x_val, y_val = x_data[val_start:test_start], y[val_start:test_start]
    x_test, y_test = x_data[test_start:], y[test_start:]

    return (x_train, y_train), (x_val, y_val), (x_test, y_test)


def _evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """평가 지표 계산."""
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred)) if len(y_true) > 1 else 0.0
    mask = y_true != 0
    if mask.sum() > 0:
        mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)
    else:
        mape = 0.0
    return {"rmse": rmse, "mae": mae, "r2": r2, "mape": mape}


def _train_with_optuna(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    n_trials: int,
    label: str = "",
) -> XGBRegressor:
    """Optuna 하이퍼파라미터 튜닝으로 XGBoost 학습."""

    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma": trial.suggest_float("gamma", 1e-8, 1.0, log=True),
        }
        model = XGBRegressor(**params, random_state=42, n_jobs=-1)
        model.fit(
            x_train, y_train,
            eval_set=[(x_val, y_val)],
            verbose=False,
        )
        y_pred = model.predict(x_val)
        return float(np.sqrt(mean_squared_error(y_val, y_pred)))

    study = optuna.create_study(direction="minimize", study_name=label)
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    logger.info(
        "%s Optuna best RMSE=%.0f (trial %d/%d)",
        label, study.best_value, study.best_trial.number, n_trials,
    )

    best_model = XGBRegressor(**study.best_params, random_state=42, n_jobs=-1)
    best_model.fit(
        x_train, y_train,
        eval_set=[(x_val, y_val)],
        verbose=False,
    )
    return best_model


# ─────────────────── CSV + DB 병합 ───────────────────


def merge_csv_prices_with_lots(
    csv_prices: dict[str, list[dict[str, int]]],
    lots: list[Any],
    db_supplement: bool = True,
) -> list[dict[str, Any]]:
    """CSV 가격 이력 + DB 토지특성 병합 → 학습용 데이터.

    Args:
        csv_prices: {pnu: [{"base_year": int, "price_per_sqm": int}, ...]}
        lots: DB에서 조회한 Lot ORM 객체 리스트
        db_supplement: CSV 이력 부족 시 DB JSONB 보충 여부

    Returns:
        list[dict] — 기존 lots_dicts와 동일한 형태 (official_prices 포함)
    """
    lot_map: dict[str, Any] = {lot.pnu: lot for lot in lots}
    merged: list[dict[str, Any]] = []

    for pnu, csv_history in csv_prices.items():
        lot = lot_map.get(pnu)
        if lot is None:
            continue

        # CSV 가격 이력을 기본으로 사용
        combined_prices = {p["base_year"]: p for p in csv_history}

        # DB JSONB에 추가 이력이 있으면 보충
        if db_supplement and lot.official_prices:
            for p in lot.official_prices:
                yr = int(p.get("base_year", 0))
                if yr > 0 and yr not in combined_prices:
                    combined_prices[yr] = {
                        "base_year": yr,
                        "price_per_sqm": int(p.get("price_per_sqm", 0)),
                    }

        prices_list = sorted(combined_prices.values(), key=lambda x: x["base_year"])

        merged.append({
            "pnu": pnu,
            "area": lot.area,
            "jimok": lot.jimok,
            "use_zone": lot.use_zone,
            "ownership": lot.ownership,
            "owner_count": lot.owner_count,
            "official_price": lot.official_price,
            "official_prices": prices_list,
        })

    logger.info(
        "병합 완료: CSV %d PNU → DB 매칭 %d 필지",
        len(csv_prices), len(merged),
    )
    return merged


# ─────────────────── 횡단면 모드 ───────────────────


def _build_cross_sectional_rows(
    lots: list[dict[str, Any]],
    building_map: dict[str, dict[str, Any]],
    sgg_stats_map: dict[str, dict[str, float]],
) -> tuple[list[list[float]], list[float]]:
    """횡단면 훈련 데이터: (features, price_per_sqm) 쌍 생성.

    각 lot의 최신 공시지가가 타겟.
    """
    features_list: list[list[float]] = []
    targets: list[float] = []

    for lot in lots:
        prices = lot.get("official_prices") or []
        if not prices:
            continue

        # 최신 가격
        sorted_prices = sorted(prices, key=lambda p: int(p.get("base_year", 0)))
        latest = sorted_prices[-1]
        price = latest.get("price_per_sqm")
        if price is None or float(price) <= 0:
            continue

        base_year = int(latest["base_year"])
        pnu = lot["pnu"]

        vec = build_cross_sectional_vector(
            area=lot.get("area"),
            jimok=lot.get("jimok"),
            use_zone=lot.get("use_zone"),
            ownership=lot.get("ownership"),
            owner_count=lot.get("owner_count"),
            base_year=base_year,
            building=building_map.get(pnu),
            sgg_stats=sgg_stats_map.get(pnu[:5]),
        )

        features_list.append(vec)
        targets.append(float(price))

    return features_list, targets


def _build_enhanced_cross_sectional_rows(
    lots: list[dict[str, Any]],
    building_map: dict[str, dict[str, Any]],
    sgg_stats_map: dict[str, dict[str, float]],
    sgg_price_stats_map: dict[str, dict[str, float]],
    sgg_growth_rates: dict[str, float],
) -> tuple[list[list[float]], list[float]]:
    """강화 횡단면 훈련 데이터: 기존 25개 + 지역 가격 컨텍스트 4개.

    각 lot의 최신 공시지가가 타겟.
    """
    features_list: list[list[float]] = []
    targets: list[float] = []

    for lot in lots:
        prices = lot.get("official_prices") or []
        if not prices:
            continue

        sorted_prices = sorted(prices, key=lambda p: int(p.get("base_year", 0)))
        latest = sorted_prices[-1]
        price = latest.get("price_per_sqm")
        if price is None or float(price) <= 0:
            continue

        base_year = int(latest["base_year"])
        pnu = lot["pnu"]
        sgg_code = pnu[:5]

        # official_price flat 컬럼 우선, 없으면 CSV/JSONB 최신 가격 사용
        current_price = lot.get("official_price") or float(price)

        vec = build_enhanced_cross_sectional_vector(
            area=lot.get("area"),
            jimok=lot.get("jimok"),
            use_zone=lot.get("use_zone"),
            ownership=lot.get("ownership"),
            owner_count=lot.get("owner_count"),
            base_year=base_year,
            building=building_map.get(pnu),
            sgg_stats=sgg_stats_map.get(sgg_code),
            current_price=current_price,
            sgg_price_stats=sgg_price_stats_map.get(sgg_code),
            sgg_growth_rate=sgg_growth_rates.get(sgg_code, DEFAULT_ANNUAL_GROWTH_RATE),
        )

        features_list.append(vec)
        targets.append(float(price))

    return features_list, targets


# ─────────────────── 시계열 모드 ───────────────────


def _build_timeseries_rows(
    lots: list[dict[str, Any]],
    building_map: dict[str, dict[str, Any]],
    sgg_stats_map: dict[str, dict[str, float]],
) -> tuple[list[list[float]], dict[int, list[float]]]:
    """시계열 훈련 데이터: (base_year features, target_year_k prices) 확장."""
    x_data: list[list[float]] = []
    y_by_offset: dict[int, list[float]] = {k: [] for k in range(1, PREDICTION_YEARS + 1)}

    for lot in lots:
        prices = lot.get("official_prices") or []
        if not prices:
            continue

        year_price: dict[int, float] = {}
        for p in prices:
            try:
                yr = int(p["base_year"])
                pr = float(p["price_per_sqm"])
                year_price[yr] = pr
            except (KeyError, ValueError, TypeError):
                continue

        if len(year_price) < 3:
            continue

        sorted_years = sorted(year_price.keys())
        pnu = lot["pnu"]
        building = building_map.get(pnu)
        sgg_stats = sgg_stats_map.get(pnu[:5])

        for base_year in sorted_years:
            targets_exist = any(
                (base_year + k) in year_price for k in range(1, PREDICTION_YEARS + 1)
            )
            if not targets_exist:
                continue

            feature_vec = build_feature_vector(
                area=lot.get("area"),
                jimok=lot.get("jimok"),
                use_zone=lot.get("use_zone"),
                ownership=lot.get("ownership"),
                owner_count=lot.get("owner_count"),
                prices=prices,
                base_year=base_year,
                building=building,
                sgg_stats=sgg_stats,
            )

            row_added = False
            for k in range(1, PREDICTION_YEARS + 1):
                target_year = base_year + k
                if target_year in year_price:
                    if not row_added:
                        x_data.append(feature_vec)
                        row_added = True
                    y_by_offset[k].append(year_price[target_year])
                else:
                    if not row_added:
                        x_data.append(feature_vec)
                        row_added = True
                    y_by_offset[k].append(float("nan"))

    return x_data, y_by_offset


# ─────────────────── ModelTrainer ───────────────────


class ModelTrainer:
    """XGBoost 훈련기 (횡단면/시계열 자동 전환)."""

    def __init__(
        self,
        model_dir: str = "./ml_models",
        n_trials: int = 50,
    ) -> None:
        self.model_dir = Path(model_dir)
        self.n_trials = n_trials
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        lots: list[dict[str, Any]],
        building_map: dict[str, dict[str, Any]],
        sgg_stats_map: dict[str, dict[str, float]],
        sgg_price_stats_map: dict[str, dict[str, float]] | None = None,
        sgg_growth_rates: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """훈련 파이프라인 실행. 데이터에 따라 자동으로 모드 결정.

        Args:
            sgg_price_stats_map: 시군구별 공시지가 통계 (enhanced 모드용)
            sgg_growth_rates: 시군구별 연간 성장률 (enhanced 모드용)
        """
        # 평균 이력 연수 계산
        history_lengths = []
        for lot in lots:
            prices = lot.get("official_prices") or []
            history_lengths.append(len(prices))
        avg_history = sum(history_lengths) / len(history_lengths) if history_lengths else 0

        # enhanced 모드: 지역 가격 통계가 제공된 경우
        use_enhanced = sgg_price_stats_map is not None and sgg_growth_rates is not None

        if avg_history >= 3.0:
            logger.info("Time-series mode (avg history=%.1f years)", avg_history)
            return self._run_timeseries(lots, building_map, sgg_stats_map)
        elif use_enhanced:
            logger.info(
                "Enhanced cross-sectional mode (avg history=%.1f years)", avg_history
            )
            return self._run_enhanced_cross_sectional(
                lots, building_map, sgg_stats_map,
                sgg_price_stats_map, sgg_growth_rates,
            )
        else:
            logger.info("Cross-sectional mode (avg history=%.1f years)", avg_history)
            return self._run_cross_sectional(lots, building_map, sgg_stats_map)

    def _run_cross_sectional(
        self,
        lots: list[dict[str, Any]],
        building_map: dict[str, dict[str, Any]],
        sgg_stats_map: dict[str, dict[str, float]],
    ) -> dict[str, Any]:
        """횡단면 모드: 1개 가격 예측 모델 + 성장률 저장."""
        logger.info("Building cross-sectional rows from %d lots...", len(lots))
        features_list, targets = _build_cross_sectional_rows(
            lots, building_map, sgg_stats_map
        )

        if not features_list:
            raise ValueError("No training data generated. Check lot data quality.")

        x_all = np.array(features_list, dtype=np.float64)
        y_all = np.array(targets, dtype=np.float64)
        logger.info(
            "Training data: %d samples, %d features", x_all.shape[0], x_all.shape[1]
        )

        # 스케일러
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_all)

        # 분할
        (x_train, y_train), (x_val, y_val), (x_test, y_test) = _time_split(
            x_scaled, y_all
        )

        # 훈련
        if len(y_train) < 50:
            logger.warning("Only %d training samples, using default params.", len(y_train))
            model = XGBRegressor(
                n_estimators=300, max_depth=6, learning_rate=0.05,
                random_state=42, n_jobs=-1,
            )
            model.fit(x_train, y_train, eval_set=[(x_val, y_val)], verbose=False)
        else:
            model = _train_with_optuna(
                x_train, y_train, x_val, y_val,
                self.n_trials, label="cross_sectional",
            )

        # 평가
        if len(x_test) > 0:
            y_pred = model.predict(x_test)
            metrics = _evaluate(y_test, y_pred)
            residual_std = float(np.std(y_test - y_pred))
        else:
            y_pred = model.predict(x_val)
            metrics = _evaluate(y_val, y_pred)
            residual_std = float(np.std(y_val - y_pred))

        logger.info(
            "Cross-sectional: RMSE=%.0f, MAE=%.0f, R2=%.4f, MAPE=%.2f%%",
            metrics["rmse"], metrics["mae"], metrics["r2"], metrics["mape"],
        )

        # 저장
        joblib.dump(model, self.model_dir / "model_base.joblib")
        joblib.dump(scaler, self.model_dir / "scaler.joblib")

        metadata = {
            "mode": "cross_sectional",
            "version": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "n_samples": int(x_all.shape[0]),
            "n_features": int(x_all.shape[1]),
            "feature_names": CROSS_SECTIONAL_FEATURE_NAMES,
            "prediction_years": PREDICTION_YEARS,
            "metrics": {"base": metrics},
            "residual_std": residual_std,
            "annual_growth_rate": DEFAULT_ANNUAL_GROWTH_RATE,
            "n_trials": self.n_trials,
            "trained_at": datetime.now().isoformat(),
        }
        (self.model_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2)
        )

        logger.info("Cross-sectional model saved to %s", self.model_dir)
        return metadata

    def _run_enhanced_cross_sectional(
        self,
        lots: list[dict[str, Any]],
        building_map: dict[str, dict[str, Any]],
        sgg_stats_map: dict[str, dict[str, float]],
        sgg_price_stats_map: dict[str, dict[str, float]],
        sgg_growth_rates: dict[str, float],
    ) -> dict[str, Any]:
        """강화 횡단면 모드: 지역 가격 컨텍스트 포함 29개 피쳐."""
        logger.info("Building enhanced cross-sectional rows from %d lots...", len(lots))
        features_list, targets = _build_enhanced_cross_sectional_rows(
            lots, building_map, sgg_stats_map, sgg_price_stats_map, sgg_growth_rates
        )

        if not features_list:
            raise ValueError("No training data generated. Check lot data quality.")

        x_all = np.array(features_list, dtype=np.float64)
        y_all = np.array(targets, dtype=np.float64)
        logger.info(
            "Training data: %d samples, %d features", x_all.shape[0], x_all.shape[1]
        )

        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_all)

        (x_train, y_train), (x_val, y_val), (x_test, y_test) = _time_split(
            x_scaled, y_all
        )

        if len(y_train) < 50:
            logger.warning("Only %d training samples, using default params.", len(y_train))
            model = XGBRegressor(
                n_estimators=300, max_depth=6, learning_rate=0.05,
                random_state=42, n_jobs=-1,
            )
            model.fit(x_train, y_train, eval_set=[(x_val, y_val)], verbose=False)
        else:
            model = _train_with_optuna(
                x_train, y_train, x_val, y_val,
                self.n_trials, label="enhanced_cross_sectional",
            )

        if len(x_test) > 0:
            y_pred = model.predict(x_test)
            metrics = _evaluate(y_test, y_pred)
            residual_std = float(np.std(y_test - y_pred))
        else:
            y_pred = model.predict(x_val)
            metrics = _evaluate(y_val, y_pred)
            residual_std = float(np.std(y_val - y_pred))

        logger.info(
            "Enhanced cross-sectional: RMSE=%.0f, MAE=%.0f, R2=%.4f, MAPE=%.2f%%",
            metrics["rmse"], metrics["mae"], metrics["r2"], metrics["mape"],
        )

        # 전체 평균 성장률 계산 (3% 고정 대신)
        if sgg_growth_rates:
            avg_growth = sum(sgg_growth_rates.values()) / len(sgg_growth_rates)
        else:
            avg_growth = DEFAULT_ANNUAL_GROWTH_RATE

        joblib.dump(model, self.model_dir / "model_base.joblib")
        joblib.dump(scaler, self.model_dir / "scaler.joblib")

        metadata = {
            "mode": "cross_sectional",
            "enhanced": True,
            "version": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "n_samples": int(x_all.shape[0]),
            "n_features": int(x_all.shape[1]),
            "feature_names": ENHANCED_CROSS_SECTIONAL_FEATURE_NAMES,
            "prediction_years": PREDICTION_YEARS,
            "metrics": {"base": metrics},
            "residual_std": residual_std,
            "annual_growth_rate": round(avg_growth, 4),
            "sgg_growth_rates": sgg_growth_rates,
            "sgg_price_stats": sgg_price_stats_map,
            "n_trials": self.n_trials,
            "trained_at": datetime.now().isoformat(),
        }
        (self.model_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2)
        )

        logger.info("Enhanced cross-sectional model saved to %s", self.model_dir)
        return metadata

    def _run_timeseries(
        self,
        lots: list[dict[str, Any]],
        building_map: dict[str, dict[str, Any]],
        sgg_stats_map: dict[str, dict[str, float]],
    ) -> dict[str, Any]:
        """시계열 모드: Direct Multi-step (10개 모델)."""
        logger.info("Building time-series rows from %d lots...", len(lots))
        x_raw, y_by_offset = _build_timeseries_rows(lots, building_map, sgg_stats_map)

        if not x_raw:
            raise ValueError("No training data generated. Check lot data quality.")

        x_all = np.array(x_raw, dtype=np.float64)
        logger.info(
            "Training data: %d samples, %d features", x_all.shape[0], x_all.shape[1]
        )

        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_all)

        metrics_all: dict[str, dict[str, float]] = {}
        residual_stds: dict[str, float] = {}

        for k in range(1, PREDICTION_YEARS + 1):
            y_k = np.array(y_by_offset[k], dtype=np.float64)
            valid_mask = ~np.isnan(y_k)
            x_valid = x_scaled[valid_mask]
            y_valid = y_k[valid_mask]

            if len(y_valid) < 50:
                logger.warning("Year +%d: %d samples, using defaults.", k, len(y_valid))
                model = XGBRegressor(
                    n_estimators=300, max_depth=6, learning_rate=0.05,
                    random_state=42, n_jobs=-1,
                )
                (x_train, y_train), (x_val, y_val), (x_test, y_test) = _time_split(
                    x_valid, y_valid
                )
                model.fit(
                    x_train, y_train, eval_set=[(x_val, y_val)], verbose=False,
                )
            else:
                (x_train, y_train), (x_val, y_val), (x_test, y_test) = _time_split(
                    x_valid, y_valid
                )
                model = _train_with_optuna(
                    x_train, y_train, x_val, y_val,
                    self.n_trials, label=f"year_{k}",
                )

            if len(x_test) > 0:
                y_pred = model.predict(x_test)
                metrics = _evaluate(y_test, y_pred)
                residual_std = float(np.std(y_test - y_pred))
            else:
                y_pred = model.predict(x_val) if len(x_val) > 0 else model.predict(x_train)
                y_true = y_val if len(x_val) > 0 else y_train
                metrics = _evaluate(y_true, y_pred)
                residual_std = float(np.std(y_true - y_pred))

            metrics_all[str(k)] = metrics
            residual_stds[str(k)] = residual_std

            joblib.dump(model, self.model_dir / f"model_year_{k}.joblib")
            logger.info(
                "Year +%d: RMSE=%.0f, MAE=%.0f, R2=%.4f, MAPE=%.2f%%",
                k, metrics["rmse"], metrics["mae"], metrics["r2"], metrics["mape"],
            )

        joblib.dump(scaler, self.model_dir / "scaler.joblib")

        metadata = {
            "mode": "time_series",
            "version": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "n_samples": int(x_all.shape[0]),
            "n_features": int(x_all.shape[1]),
            "feature_names": TIMESERIES_FEATURE_NAMES,
            "prediction_years": PREDICTION_YEARS,
            "metrics": metrics_all,
            "residual_stds": residual_stds,
            "n_trials": self.n_trials,
            "trained_at": datetime.now().isoformat(),
        }
        (self.model_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2)
        )

        logger.info("Time-series models saved to %s", self.model_dir)
        return metadata
