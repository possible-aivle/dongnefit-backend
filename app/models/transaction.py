"""실거래가(매매/전월세) 및 공시지가 모델."""

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


class RealEstateSale(PublicDataBase, table=True):
    """부동산 매매 실거래가 테이블.

    토지/단독다가구/연립다세대/아파트/오피스텔 매매 실거래가.
    https://rt.molit.go.kr/pt/xls/xls.do?mobileAt=
    """

    __tablename__ = "real_estate_sales"

    # ── 핵심 식별 필드 ──
    pnu: str | None = Field(
        default=None,
        max_length=19,
        index=True,
        description="필지고유번호 (매칭 가능한 경우)",
    )
    property_type: PropertyType = Field(
        sa_column=Column(
            Enum(PropertyType, name="property_type_enum", create_constraint=False),
            nullable=False,
        ),
        description="부동산 유형",
    )

    # ── 위치 정보 ──
    sigungu: str | None = Field(
        default=None, max_length=100, index=True, description="시군구"
    )
    lot_number: str | None = Field(
        default=None, max_length=30, description="번지"
    )
    main_lot_number: str | None = Field(
        default=None, max_length=10, description="본번"
    )
    sub_lot_number: str | None = Field(
        default=None, max_length=10, description="부번"
    )
    road_name: str | None = Field(
        default=None, max_length=200, description="도로명"
    )

    # ── 건물 정보 ──
    building_name: str | None = Field(
        default=None, max_length=200, index=True, description="단지명/건물명",
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
    contract_area: float | None = Field(
        default=None, description="계약면적 (㎡, 토지)"
    )
    floor: str | None = Field(default=None, max_length=10, description="층")
    dong: str | None = Field(default=None, max_length=50, description="동 (아파트)")
    build_year: int | None = Field(default=None, description="건축년도")
    housing_type: str | None = Field(
        default=None, max_length=30, description="주택유형"
    )

    # ── 매매 거래 정보 ──
    transaction_date: date | None = Field(default=None, index=True, description="계약일")
    transaction_amount: int | None = Field(default=None, description="거래금액 (만원)")
    buyer_type: str | None = Field(
        default=None, max_length=20, description="매수자 (개인/법인)"
    )
    seller_type: str | None = Field(
        default=None, max_length=20, description="매도자 (개인/법인)"
    )
    deal_type: str | None = Field(
        default=None, max_length=30, description="거래유형 (중개거래/직거래 등)"
    )
    broker_location: str | None = Field(
        default=None, max_length=100, description="중개사소재지"
    )
    registration_date: str | None = Field(
        default=None, max_length=20, description="등기일자"
    )
    cancellation_date: str | None = Field(
        default=None, max_length=20, description="해제사유발생일"
    )

    # ── 토지 전용 필드 ──
    land_category: str | None = Field(
        default=None, max_length=20, description="지목 (토지)"
    )
    use_area: str | None = Field(
        default=None, max_length=50, description="용도지역 (토지)"
    )
    road_condition: str | None = Field(
        default=None, max_length=30, description="도로조건 (토지/단독다가구)"
    )
    share_type: str | None = Field(
        default=None, max_length=20, description="지분구분 (토지)"
    )


class RealEstateRental(PublicDataBase, table=True):
    """부동산 전월세 실거래가 테이블.

    토지 제외, 단독다가구/연립다세대/아파트/오피스텔 전월세 실거래가.
    https://rt.molit.go.kr/pt/xls/xls.do?mobileAt=
    """

    __tablename__ = "real_estate_rentals"

    # ── 핵심 식별 필드 ──
    pnu: str | None = Field(
        default=None,
        max_length=19,
        index=True,
        description="필지고유번호 (매칭 가능한 경우)",
    )
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
    sigungu: str | None = Field(
        default=None, max_length=100, index=True, description="시군구"
    )
    lot_number: str | None = Field(
        default=None, max_length=30, description="번지"
    )
    main_lot_number: str | None = Field(
        default=None, max_length=10, description="본번"
    )
    sub_lot_number: str | None = Field(
        default=None, max_length=10, description="부번"
    )
    road_name: str | None = Field(
        default=None, max_length=200, description="도로명"
    )

    # ── 건물 정보 ──
    building_name: str | None = Field(
        default=None, max_length=200, index=True, description="단지명/건물명",
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
    dong: str | None = Field(default=None, max_length=50, description="동 (아파트)")
    build_year: int | None = Field(default=None, description="건축년도")
    housing_type: str | None = Field(
        default=None, max_length=30, description="주택유형"
    )

    # ── 전월세 거래 정보 ──
    transaction_date: date | None = Field(default=None, index=True, description="계약일")
    rent_type: str | None = Field(
        default=None, max_length=10, description="전월세구분 (전세/월세)"
    )
    deposit: int | None = Field(default=None, description="보증금 (만원)")
    monthly_rent_amount: int | None = Field(default=None, description="월세금 (만원)")
    contract_period: str | None = Field(
        default=None, max_length=30, description="계약기간 (예: 202604~202804)"
    )
    contract_type: str | None = Field(
        default=None, max_length=10, description="계약구분 (신규/갱신)"
    )
    renewal_right_used: str | None = Field(
        default=None, max_length=10, description="갱신요구권 사용 여부"
    )
    previous_deposit: int | None = Field(
        default=None, description="종전계약 보증금 (만원)"
    )
    previous_monthly_rent: int | None = Field(
        default=None, description="종전계약 월세 (만원)"
    )
    deal_type: str | None = Field(
        default=None, max_length=30, description="거래유형 (중개거래/직거래 등)"
    )
    broker_location: str | None = Field(
        default=None, max_length=100, description="중개사소재지"
    )
