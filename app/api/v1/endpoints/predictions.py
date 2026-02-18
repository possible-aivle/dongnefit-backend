"""공시지가 예측 엔드포인트."""

import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.prediction import PredictionResponse
from app.services.prediction.service import PredictionService

router = APIRouter()

PNU_PATTERN = re.compile(r"^\d{19}$")


def _get_prediction_service(request: Request) -> PredictionService:
    """app.state에서 PredictionService 인스턴스 가져오기."""
    service: PredictionService | None = getattr(request.app.state, "prediction_service", None)
    if service is None or not service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="예측 모델이 로드되지 않았습니다. 서버 관리자에게 문의하세요.",
        )
    return service


@router.get(
    "/{pnu}",
    response_model=PredictionResponse,
    summary="공시지가 10년 예측",
    description="PNU(필지고유번호)에 대해 향후 10년간의 공시지가를 예측합니다.",
    responses={
        400: {"description": "잘못된 PNU 형식"},
        404: {"description": "필지를 찾을 수 없음"},
        422: {"description": "공시지가 이력 부족"},
        503: {"description": "예측 모델 미로드"},
    },
)
async def predict_land_price(
    pnu: str,
    db: AsyncSession = Depends(get_db),
    service: PredictionService = Depends(_get_prediction_service),
) -> PredictionResponse:
    """PNU에 대한 공시지가 10년 예측 조회."""
    if not PNU_PATTERN.match(pnu):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PNU는 19자리 숫자여야 합니다.",
        )

    try:
        return await service.predict(db, pnu)
    except ValueError as e:
        msg = str(e)
        if "찾을 수 없습니다" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=msg,
        ) from e
