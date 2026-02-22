"""실거래가(매매/전월세) 모델."""

from datetime import date

from sqlalchemy import BigInteger, Column, Enum, Index, UniqueConstraint
from sqlmodel import Field

from app.models.base import PublicDataBase
from app.models.enums import PropertyType, TransactionType


class RealEstateSale(PublicDataBase, table=True):
    """부동산 매매 실거래가 테이블.

    토지/단독다가구/연립다세대/아파트/오피스텔 매매 실거래가.
    https://rt.molit.go.kr/pt/xls/xls.do?mobileAt=
    """

    __tablename__ = "local_real_estate_sales"
    __table_args__ = (
        Index("ix_sales_sgg_txdate", "sgg_code", "transaction_date"),
    )

    # ── 핵심 식별 필드 ──
    property_type: PropertyType = Field(
        sa_column=Column(
            Enum(PropertyType, name="property_type_enum", create_constraint=False),
            nullable=False,
        ),
        description="부동산 유형",
    )

    # ── 위치 정보 ──
    address: str | None = Field(
        default=None, max_length=200, index=True, description="주소 (시군구 + 번지)"
    )
    sgg_code: str | None = Field(
        default=None, max_length=5, description="시군구코드 (5자리, 시군구 텍스트에서 추출)"
    )

    # ── 건물 정보 ──
    building_name: str | None = Field(
        default=None, max_length=200, description="단지명/건물명",
    )
    exclusive_area: float | None = Field(
        default=None, description="전용면적 (㎡)"
    )
    land_area: float | None = Field(
        default=None, description="대지면적/대지권면적 (㎡)"
    )
    floor_area: float | None = Field(
        default=None, description="연면적 (㎡, 단독다가구)"
    )
    floor: str | None = Field(default=None, max_length=10, description="층")
    build_year: int | None = Field(default=None, description="건축년도")

    # ── 매매 거래 정보 ──
    transaction_date: date | None = Field(default=None, description="계약일")
    transaction_amount: int | None = Field(
        default=None, sa_column=Column(BigInteger, nullable=True), description="거래금액 (만원)"
    )
    deal_type: str | None = Field(
        default=None, max_length=30, description="거래유형 (중개거래/직거래 등)"
    )



class RealEstateRental(PublicDataBase, table=True):
    """부동산 전월세 실거래가 테이블.

    토지 제외, 단독다가구/연립다세대/아파트/오피스텔 전월세 실거래가.
    https://rt.molit.go.kr/pt/xls/xls.do?mobileAt=
    """

    __tablename__ = "local_real_estate_rentals"
    __table_args__ = (
        Index("ix_rentals_sgg_txdate", "sgg_code", "transaction_date"),
    )

    # ── 핵심 식별 필드 ──
    property_type: PropertyType = Field(
        sa_column=Column(
            Enum(PropertyType, name="property_type_enum", create_constraint=False),
            nullable=False,
        ),
        description="부동산 유형",
    )
    transaction_type: TransactionType = Field(
        sa_column=Column(
            Enum(TransactionType, name="transaction_type_enum", create_constraint=False),
            nullable=False,
        ),
        description="거래 유형 (전세/월세)",
    )

    # ── 위치 정보 ──
    address: str | None = Field(
        default=None, max_length=200, index=True, description="주소 (시군구 + 번지)"
    )
    sgg_code: str | None = Field(
        default=None, max_length=5, description="시군구코드 (5자리, 시군구 텍스트에서 추출)"
    )

    # ── 건물 정보 ──
    building_name: str | None = Field(
        default=None, max_length=200, description="단지명/건물명",
    )
    exclusive_area: float | None = Field(
        default=None, description="전용면적 (㎡)"
    )
    land_area: float | None = Field(
        default=None, description="대지면적/대지권면적 (㎡)"
    )
    floor_area: float | None = Field(
        default=None, description="연면적 (㎡, 단독다가구)"
    )
    floor: str | None = Field(default=None, max_length=10, description="층")
    build_year: int | None = Field(default=None, description="건축년도")

    # ── 전월세 거래 정보 ──
    transaction_date: date | None = Field(default=None, description="계약일")
    deposit: int | None = Field(
        default=None, sa_column=Column(BigInteger, nullable=True), description="보증금 (만원)"
    )
    monthly_rent_amount: int | None = Field(
        default=None, sa_column=Column(BigInteger, nullable=True), description="월세금 (만원)"
    )
    contract_period: str | None = Field(
        default=None, max_length=30, description="계약기간 (예: 202604~202804)"
    )
    contract_type: str | None = Field(
        default=None, max_length=10, description="계약구분 (신규/갱신)"
    )
    deal_type: str | None = Field(
        default=None, max_length=30, description="거래유형 (중개거래/직거래 등)"
    )
