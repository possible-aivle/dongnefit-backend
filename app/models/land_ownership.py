"""토지소유정보 모델 (AL_D401)."""

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.models.base import PublicDataBase


class LandOwnership(PublicDataBase, table=True):
    """토지소유정보 테이블.

    vworld csv 데이터 기반 (AL_D401).
    한 필지에 공유자가 여러 명일 수 있으므로 pnu + co_owner_seq로 유니크 제약.
    """

    __tablename__ = "land_ownerships"
    __table_args__ = (
        UniqueConstraint("pnu", "co_owner_seq", name="uq_land_ownership_pnu_seq"),
    )

    pnu: str = Field(
        max_length=19,
        description="필지고유번호",
        index=True
    )
    base_year_month: str = Field(max_length=7, description="기준연월 (YYYY-MM)")
    co_owner_seq: str = Field(max_length=6, description="공유인일련번호")
    ownership_type: str | None = Field(
        default=None, max_length=20, description="소유구분 (개인/국유/시유 등)"
    )
    ownership_change_reason: str | None = Field(
        default=None, max_length=30, description="소유권변동원인 (매매/상속 등)"
    )
    ownership_change_date: str | None = Field(
        default=None, max_length=10, description="소유권변동일자 (YYYY-MM-DD)"
    )
    owner_count: int | None = Field(default=None, description="공유인수")
