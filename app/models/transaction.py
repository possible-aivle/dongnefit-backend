"""실거래가 및 공시지가 모델."""

from datetime import date

from sqlalchemy import Column, Enum, UniqueConstraint
from sqlmodel import Field

from app.models.base import PublicDataBase
from app.models.enums import PropertyType, TransactionType


class OfficialLandPrice(PublicDataBase, table=True):
    """개별공시지가 테이블.

    사업성 분석 필수 데이터.
    vworld csv 데이터 기반 (AL_D151, 13개 CSV 컬럼).
    """

    __tablename__ = "official_land_prices"
    __table_args__ = (UniqueConstraint("pnu", "base_year", name="uq_official_price_pnu_year"),)

    pnu: str = Field(
        max_length=19,
        foreign_key="lots.pnu",
        index=True,
        description="필지고유번호",
    )
    base_year: int = Field(description="기준연도")
    price_per_sqm: int | None = Field(default=None, description="공시지가(원/㎡)")

    # AL_D151 컬럼정의서 기반
    bjd_code: str | None = Field(default=None, max_length=10, description="법정동코드")
    bjd_name: str | None = Field(default=None, max_length=100, description="법정동명")
    special_land_code: str | None = Field(default=None, max_length=2, description="특수지구분코드")
    special_land_name: str | None = Field(default=None, max_length=20, description="특수지구분명")
    jibun: str | None = Field(default=None, max_length=20, description="지번")
    base_month: int | None = Field(default=None, description="기준월")
    announcement_date: date | None = Field(default=None, description="공시일자")
    is_standard: bool | None = Field(default=None, description="표준지여부")
    data_base_date: str | None = Field(default=None, max_length=10, description="데이터기준일자")
    source_sigungu_code: str | None = Field(
        default=None, max_length=5, description="원천시도시군구코드"
    )


class RealEstateTransaction(PublicDataBase, table=True):
    """부동산 실거래가 테이블.

    사업성 분석 필수 데이터.
    토지/상업업무용/단독다가구/연립다세대/아파트/오피스텔 실거래가 통합.
    매매 및 전월세 포함.
    rt.molit.go.kr 데이터 기반 (달별 csv, 현재 API로 변경됨).

    주의: 전월세 데이터 업로드 시 해당 전 기간의 전월세전환율 데이터가 먼저 필요.
    """

    __tablename__ = "real_estate_transactions"

    pnu: str | None = Field(
        default=None,
        max_length=19,
        index=True,
        description="필지고유번호 (매칭 가능한 경우)",
    )
    property_type: PropertyType = Field(
        sa_column=Column(
            Enum(PropertyType, name="property_type_enum", create_constraint=True),
            nullable=False,
        ),
        description="부동산 유형",
    )
    transaction_type: TransactionType = Field(
        sa_column=Column(
            Enum(TransactionType, name="transaction_type_enum", create_constraint=True),
            nullable=False,
        ),
        description="거래 유형 (매매/전세/월세)",
    )
    transaction_date: date | None = Field(default=None, description="거래일")
    transaction_amount: int | None = Field(default=None, description="거래금액 (만원)")
