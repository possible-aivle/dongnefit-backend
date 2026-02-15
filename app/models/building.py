"""건물 관련 모델 (건축물대장 표제부, 층별개요, GIS건물통합정보)."""

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
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


class GisBuildingIntegrated(PublicDataBase, table=True):
    """GIS건물통합정보 테이블.

    vworld shp 데이터 기반 (AL_D010, 29개 SHP 컬럼).
    건물 공간정보(geometry) + 속성 데이터 통합 테이블.
    geometry는 GeoJSON 형태로 JSONB에 저장.

    제외 컬럼: 원천도형ID, GIS건물통합식별번호, 특수지코드,
              건축물용도코드, 건축물구조코드, 참조체계연계키, 원천시도시군구코드.
    """

    __tablename__ = "gis_building_integrated"
    __table_args__ = (UniqueConstraint("pnu", "building_id", name="uq_gis_building_pnu_bid"),)

    pnu: str = Field(
        max_length=19,
        foreign_key="lots.pnu",
        index=True,
        description="필지고유번호 (고유번호)",
    )
    bjd_code: str | None = Field(default=None, max_length=10, description="법정동코드")
    bjd_name: str | None = Field(default=None, max_length=100, description="법정동명")
    jibun: str | None = Field(default=None, max_length=20, description="지번")
    special_land_name: str | None = Field(default=None, max_length=50, description="특수지구분명")
    use_name: str | None = Field(default=None, max_length=100, description="건축물용도명")
    structure_name: str | None = Field(default=None, max_length=100, description="건축물구조명")
    building_area: float | None = Field(default=None, description="건축물면적(㎡)")
    approval_date: str | None = Field(default=None, max_length=10, description="사용승인일자")
    total_floor_area: float | None = Field(default=None, description="연면적(㎡)")
    site_area: float | None = Field(default=None, description="대지면적(㎡)")
    height: float | None = Field(default=None, description="높이(m)")
    building_coverage_ratio: float | None = Field(default=None, description="건폐율(%)")
    floor_area_ratio: float | None = Field(default=None, description="용적율(%)")
    building_id: str | None = Field(default=None, max_length=28, description="건축물ID")
    is_violation: str | None = Field(default=None, max_length=2, description="위반건축물여부")
    data_base_date: str | None = Field(default=None, max_length=10, description="데이터기준일자")
    building_name: str | None = Field(default=None, max_length=100, description="건물명")
    building_dong_name: str | None = Field(default=None, max_length=100, description="건물동명")
    above_ground_floors: int | None = Field(default=None, description="지상층수")
    underground_floors: int | None = Field(default=None, description="지하층수")
    data_change_date: str | None = Field(
        default=None, max_length=10, description="데이터생성변경일자"
    )
    geometry: dict | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="GeoJSON geometry",
    )
