"""Pydantic schemas for request/response validation."""

from app.schemas.administrative import (
    AdministrativeEmdCreate,
    AdministrativeEmdRead,
    AdministrativeSggCreate,
    AdministrativeSggRead,
    AdministrativeSidoCreate,
    AdministrativeSidoRead,
)
from app.schemas.base import (
    BaseSchema,
    GeoJSON,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    TimestampSchema,
    wkb_to_geojson,
    wkb_to_shapely,
)
from app.schemas.building import (
    BuildingRegisterAreaCreate,
    BuildingRegisterAreaRead,
    BuildingRegisterFloorDetailCreate,
    BuildingRegisterFloorDetailRead,
    BuildingRegisterGeneralCreate,
    BuildingRegisterGeneralRead,
    BuildingRegisterHeaderCreate,
    BuildingRegisterHeaderRead,
    GisBuildingIntegratedCreate,
    GisBuildingIntegratedRead,
)
from app.schemas.lot import (
    AncillaryLandCreate,
    AncillaryLandRead,
    LotCreate,
    LotRead,
)
from app.schemas.spatial import (
    RoadCenterLineCreate,
    RoadCenterLineRead,
    UseRegionDistrictCreate,
    UseRegionDistrictRead,
)
from app.schemas.transaction import (
    RealEstateRentalCreate,
    RealEstateRentalRead,
    RealEstateSaleCreate,
    RealEstateSaleRead,
)

__all__ = [
    # Base
    "BaseSchema",
    "TimestampSchema",
    "PaginationParams",
    "PaginationMeta",
    "PaginatedResponse",
    # Geometry
    "GeoJSON",
    "wkb_to_geojson",
    "wkb_to_shapely",
    # Lot
    "LotCreate",
    "LotRead",
    "AncillaryLandCreate",
    "AncillaryLandRead",
    # Administrative
    "AdministrativeSidoCreate",
    "AdministrativeSidoRead",
    "AdministrativeSggCreate",
    "AdministrativeSggRead",
    "AdministrativeEmdCreate",
    "AdministrativeEmdRead",
    # Building
    "BuildingRegisterHeaderCreate",
    "BuildingRegisterHeaderRead",
    "BuildingRegisterGeneralCreate",
    "BuildingRegisterGeneralRead",
    "BuildingRegisterFloorDetailCreate",
    "BuildingRegisterFloorDetailRead",
    "BuildingRegisterAreaCreate",
    "BuildingRegisterAreaRead",
    "GisBuildingIntegratedCreate",
    "GisBuildingIntegratedRead",
    # Transaction
    "RealEstateSaleCreate",
    "RealEstateSaleRead",
    "RealEstateRentalCreate",
    "RealEstateRentalRead",
    # Spatial
    "RoadCenterLineCreate",
    "RoadCenterLineRead",
    "UseRegionDistrictCreate",
    "UseRegionDistrictRead",
]
