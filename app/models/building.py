"""건물 관련 모델 (건축물대장 표제부, 층별개요)."""

from sqlmodel import Field

from app.models.base import PublicDataBase


class BuildingRegisterHeader(PublicDataBase, table=True):
    """건축물대장 표제부 테이블.

    서브 데이터.
    공공데이터포털 대용량 제공 서비스 > 건축물대장 > 표제부.
    txt 포맷.
    """

    __tablename__ = "building_register_headers"

    pnu: str = Field(
        max_length=19,
        foreign_key="lots.pnu",
        index=True,
        description="필지고유번호",
    )


class BuildingRegisterFloorDetail(PublicDataBase, table=True):
    """건축물대장 층별개요 테이블.

    서브 데이터.
    공공데이터포털 대용량 제공 서비스 > 건축물대장 > 층별개요.
    txt 포맷.
    """

    __tablename__ = "building_register_floor_details"

    pnu: str = Field(
        max_length=19,
        foreign_key="lots.pnu",
        index=True,
        description="필지고유번호",
    )
