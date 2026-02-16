"""건물 관련 모델 (건축물대장 표제부, 총괄표제부, 층별개요, 전유공용면적, 부속지번, GIS건물통합정보)."""

from typing import Any

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.models.base import PublicDataBase, geometry_column


class BuildingRegisterHeader(PublicDataBase, table=True):
    """건축물대장 표제부 테이블.

    공공데이터포털 대용량 제공 서비스 > 건축물대장 > 표제부 (mart_djy_03.txt).
    동별 건축물 정보를 관리합니다.
    """

    __tablename__ = "building_register_headers"
    __table_args__ = (
        UniqueConstraint("mgm_bldrgst_pk", name="uq_bldrgst_header_pk"),
    )

    mgm_bldrgst_pk: str = Field(max_length=33, index=True, description="관리 건축물대장 PK")
    pnu: str = Field(
        max_length=19,
        # lots.pnu 참조: FK 대신 인덱스로 관리 (파이프라인 독립 적재 지원)
        index=True,
        description="필지고유번호",
    )
    building_name: str | None = Field(default=None, max_length=100, description="건물명")
    site_area: float | None = Field(default=None, description="대지면적(㎡)")
    building_area: float | None = Field(default=None, description="건축면적(㎡)")
    bcr: float | None = Field(default=None, description="건폐율(%)")
    total_floor_area: float | None = Field(default=None, description="연면적(㎡)")
    far: float | None = Field(default=None, description="용적률(%)")
    structure_name: str | None = Field(default=None, max_length=100, description="구조코드명")
    main_use_name: str | None = Field(default=None, max_length=100, description="주용도코드명")
    household_count: int | None = Field(default=None, description="세대수")
    height: float | None = Field(default=None, description="높이(m)")
    above_ground_floors: int | None = Field(default=None, description="지상층수")
    underground_floors: int | None = Field(default=None, description="지하층수")
    approval_date: str | None = Field(default=None, max_length=8, description="사용승인일")


class BuildingRegisterGeneral(PublicDataBase, table=True):
    """건축물대장 총괄표제부 테이블.

    공공데이터포털 대용량 제공 서비스 > 건축물대장 > 총괄표제부 (mart_djy_02.txt).
    건물 전체 총괄 정보를 관리합니다.
    """

    __tablename__ = "building_register_generals"
    __table_args__ = (
        UniqueConstraint("mgm_bldrgst_pk", name="uq_bldrgst_general_pk"),
    )

    mgm_bldrgst_pk: str = Field(max_length=33, index=True, description="관리 건축물대장 PK")
    pnu: str = Field(
        max_length=19,
        # lots.pnu 참조: FK 대신 인덱스로 관리 (파이프라인 독립 적재 지원)
        index=True,
        description="필지고유번호",
    )
    building_name: str | None = Field(default=None, max_length=100, description="건물명")
    site_area: float | None = Field(default=None, description="대지면적(㎡)")
    building_area: float | None = Field(default=None, description="건축면적(㎡)")
    bcr: float | None = Field(default=None, description="건폐율(%)")
    total_floor_area: float | None = Field(default=None, description="연면적(㎡)")
    far: float | None = Field(default=None, description="용적률(%)")
    main_use_name: str | None = Field(default=None, max_length=100, description="주용도코드명")
    household_count: int | None = Field(default=None, description="세대수")
    total_parking: int | None = Field(default=None, description="총주차수")
    approval_date: str | None = Field(default=None, max_length=8, description="사용승인일")


class BuildingRegisterFloorDetail(PublicDataBase, table=True):
    """건축물대장 층별개요 테이블.

    공공데이터포털 대용량 제공 서비스 > 건축물대장 > 층별개요 (mart_djy_04.txt).
    동별 층별 용도 및 면적 정보를 관리합니다.
    """

    __tablename__ = "building_register_floor_details"

    mgm_bldrgst_pk: str = Field(max_length=33, index=True, description="관리 건축물대장 PK")
    pnu: str = Field(
        max_length=19,
        # lots.pnu 참조: FK 대신 인덱스로 관리 (파이프라인 독립 적재 지원)
        index=True,
        description="필지고유번호",
    )
    floor_type_name: str | None = Field(default=None, max_length=100, description="층구분코드명")
    floor_no: int | None = Field(default=None, description="층번호")
    main_use_name: str | None = Field(default=None, max_length=100, description="주용도코드명")
    area: float | None = Field(default=None, description="면적(㎡)")


class BuildingRegisterArea(PublicDataBase, table=True):
    """건축물대장 전유공용면적 테이블.

    공공데이터포털 대용량 제공 서비스 > 건축물대장 > 전유공용면적 (mart_djy_06.txt).
    세대별 전유면적/공용면적을 관리하여 공급면적 도출에 사용합니다.
    """

    __tablename__ = "building_register_areas"

    mgm_bldrgst_pk: str = Field(max_length=33, index=True, description="관리 건축물대장 PK")
    pnu: str = Field(
        max_length=19,
        # lots.pnu 참조: FK 대신 인덱스로 관리 (파이프라인 독립 적재 지원)
        index=True,
        description="필지고유번호",
    )
    dong_name: str | None = Field(default=None, max_length=100, description="동명")
    ho_name: str | None = Field(default=None, max_length=100, description="호명")
    floor_no: int | None = Field(default=None, description="층번호")
    exclu_common_type: str | None = Field(
        default=None, max_length=1, description="전유공용구분코드 (1:전유, 2:공용)"
    )
    area: float | None = Field(default=None, description="면적(㎡)")


class BuildingRegisterAncillaryLot(PublicDataBase, table=True):
    """건축물대장 부속지번 테이블.

    공공데이터포털 대용량 제공 서비스 > 건축물대장 > 부속지번 (mart_djy_05.txt).
    건축물에 소속된 부속 필지 정보를 관리합니다.
    """

    __tablename__ = "building_register_ancillary_lots"

    mgm_bldrgst_pk: str = Field(max_length=33, index=True, description="관리 건축물대장 PK")
    pnu: str = Field(
        max_length=19,
        # lots.pnu 참조: FK 대신 인덱스로 관리 (파이프라인 독립 적재 지원)
        index=True,
        description="필지고유번호 (본 건물)",
    )
    atch_pnu: str | None = Field(
        default=None, max_length=19, index=True, description="부속 필지고유번호"
    )
    created_date: str | None = Field(default=None, max_length=8, description="생성일자")


class GisBuildingIntegrated(PublicDataBase, table=True):
    """GIS건물통합정보 테이블.

    vworld shp 데이터 기반 (AL_D010).
    건물 공간정보(geometry) + 속성 데이터 통합 테이블.
    geometry는 PostGIS Geometry 컬럼으로 저장 (SRID=4326).
    """

    __tablename__ = "gis_building_integrated"
    __table_args__ = (UniqueConstraint("pnu", "building_id", name="uq_gis_building_pnu_bid"),)

    pnu: str = Field(
        max_length=19,
        # lots.pnu 참조: FK 대신 인덱스로 관리 (파이프라인 독립 적재 지원)
        index=True,
        description="필지고유번호 (고유번호)",
    )
    use_name: str | None = Field(default=None, max_length=100, description="건축물용도명")
    building_area: float | None = Field(default=None, description="건축물면적(㎡)")
    approval_date: str | None = Field(default=None, max_length=10, description="사용승인일자")
    total_floor_area: float | None = Field(default=None, description="연면적(㎡)")
    site_area: float | None = Field(default=None, description="대지면적(㎡)")
    height: float | None = Field(default=None, description="높이(m)")
    building_id: str | None = Field(default=None, max_length=28, description="건축물ID")
    building_name: str | None = Field(default=None, max_length=100, description="건물명")
    above_ground_floors: int | None = Field(default=None, description="지상층수")
    underground_floors: int | None = Field(default=None, description="지하층수")
    geometry: Any = geometry_column(description="건물 경계 (Polygon/MultiPolygon)")
