"""토지 관련 모델 (토지특성, 토지이용계획, 토지임야정보)."""

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.models.base import PublicDataBase


class LandCharacteristic(PublicDataBase, table=True):
    """토지특성정보 테이블.

    코어 데이터 - 최신성 중요.
    vworld csv 데이터 기반 (AL_D195, 26개 CSV 컬럼).
    """

    __tablename__ = "land_characteristics"
    __table_args__ = (UniqueConstraint("pnu", "data_year", name="uq_land_char_pnu_year"),)

    pnu: str = Field(
        max_length=19,
        foreign_key="lots.pnu",
        index=True,
        description="필지고유번호",
    )
    data_year: int = Field(description="기준년도")

    jimok_name: str | None = Field(default=None, max_length=20, description="지목명")
    land_area: float | None = Field(default=None, description="토지면적(㎡)")
    use_zone_name: str | None = Field(default=None, max_length=50, description="용도지역명")
    land_use_name: str | None = Field(default=None, max_length=30, description="토지이용상황")
    official_price: int | None = Field(default=None, description="공시지가(원)")


class LandUsePlan(PublicDataBase, table=True):
    """토지이용계획정보 테이블.

    코어 데이터 - 최신성 중요.
    vworld csv 데이터 기반 (AL_D154, 15개 CSV 컬럼).
    """

    __tablename__ = "land_use_plans"
    __table_args__ = (UniqueConstraint("pnu", "data_year", name="uq_land_use_pnu_year"),)

    pnu: str = Field(
        max_length=19,
        foreign_key="lots.pnu",
        index=True,
        description="필지고유번호",
    )
    data_year: int = Field(description="기준년도")

    use_district_name: str | None = Field(default=None, max_length=50, description="용도지역지구명")


class LandAndForestInfo(PublicDataBase, table=True):
    """토지임야정보 테이블.

    면적은 토지특성보다 이 테이블의 데이터가 신뢰도가 높음.
    소유인 수 업데이트 용도.
    vworld csv 데이터 기반 (AL_D003, 16개 CSV 컬럼).
    """

    __tablename__ = "land_and_forest_infos"
    __table_args__ = (UniqueConstraint("pnu", "data_year", name="uq_land_forest_pnu_year"),)

    pnu: str = Field(
        max_length=19,
        foreign_key="lots.pnu",
        index=True,
        description="필지고유번호",
    )
    data_year: int = Field(description="기준년도")

    jimok_name: str | None = Field(default=None, max_length=20, description="지목명")
    area: float | None = Field(default=None, description="면적(㎡)")
    ownership_name: str | None = Field(default=None, max_length=20, description="소유구분명")
    owner_count: int | None = Field(default=None, description="소유(공유)인수")
