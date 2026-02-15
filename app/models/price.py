"""주택가격 관련 모델 (개별주택가격, 공동주택가격)."""

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.models.base import PublicDataBase


class IndividualHousePrice(PublicDataBase, table=True):
    """개별주택가격정보 테이블.

    사업성 분석 참고 데이터.
    vworld csv 데이터 기반 (AL_D169, 19개 CSV 컬럼).
    """

    __tablename__ = "individual_house_prices"
    __table_args__ = (UniqueConstraint("pnu", "base_year", name="uq_ind_house_pnu_year"),)

    pnu: str = Field(
        max_length=19,
        foreign_key="lots.pnu",
        index=True,
        description="필지고유번호",
    )
    base_year: int = Field(description="기준년도")
    house_price: int | None = Field(default=None, description="주택가격(원)")


class ApartmentPrice(PublicDataBase, table=True):
    """공동주택가격정보 테이블.

    사업성 분석 참고 데이터.
    vworld csv 데이터 기반 (AL_D167, 19개 CSV 컬럼).
    """

    __tablename__ = "apartment_prices"
    __table_args__ = (
        UniqueConstraint(
            "pnu",
            "base_year",
            "dong_name",
            "ho_name",
            name="uq_apt_price",
        ),
    )

    pnu: str = Field(
        max_length=19,
        foreign_key="lots.pnu",
        index=True,
        description="필지고유번호",
    )
    base_year: int = Field(description="기준년도")
    apt_type_name: str | None = Field(default=None, max_length=20, description="공동주택구분명")
    apt_name: str | None = Field(default=None, max_length=100, description="공동주택명")
    dong_name: str | None = Field(default=None, max_length=50, description="동명")
    ho_name: str | None = Field(default=None, max_length=10, description="호명")
    exclusive_area: float | None = Field(default=None, description="전용면적(㎡)")
    official_price: int | None = Field(default=None, description="공시가격(원)")
