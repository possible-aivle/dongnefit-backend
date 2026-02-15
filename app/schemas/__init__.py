"""Pydantic schemas for request/response validation."""

from app.schemas.administrative import (
    AdministrativeDivisionCreate,
    AdministrativeDivisionRead,
    AdministrativeEmdCreate,
    AdministrativeEmdRead,
)
from app.schemas.base import (
    BaseSchema,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    TimestampSchema,
)
from app.schemas.building import (
    BuildingRegisterFloorDetailCreate,
    BuildingRegisterFloorDetailRead,
    BuildingRegisterHeaderCreate,
    BuildingRegisterHeaderRead,
    GisBuildingIntegratedCreate,
    GisBuildingIntegratedRead,
)
from app.schemas.land import (
    LandAndForestInfoCreate,
    LandAndForestInfoRead,
    LandCharacteristicCreate,
    LandCharacteristicRead,
    LandUsePlanCreate,
    LandUsePlanRead,
)
from app.schemas.land_ownership import (
    LandOwnershipCreate,
    LandOwnershipRead,
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
    OfficialLandPriceCreate,
    OfficialLandPriceRead,
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
    # Lot
    "LotCreate",
    "LotRead",
    "AncillaryLandCreate",
    "AncillaryLandRead",
    # Administrative
    "AdministrativeDivisionCreate",
    "AdministrativeDivisionRead",
    "AdministrativeEmdCreate",
    "AdministrativeEmdRead",
    # Land
    "LandCharacteristicCreate",
    "LandCharacteristicRead",
    "LandUsePlanCreate",
    "LandUsePlanRead",
    "LandAndForestInfoCreate",
    "LandAndForestInfoRead",
    "LandOwnershipCreate",
    "LandOwnershipRead",
    # Building
    "BuildingRegisterHeaderCreate",
    "BuildingRegisterHeaderRead",
    "BuildingRegisterFloorDetailCreate",
    "BuildingRegisterFloorDetailRead",
    "GisBuildingIntegratedCreate",
    "GisBuildingIntegratedRead",
    # Transaction
    "OfficialLandPriceCreate",
    "OfficialLandPriceRead",
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
