"""Database models."""

from app.models.administrative import AdministrativeDivision, AdministrativeEmd
from app.models.base import PublicDataBase, TimestampMixin
from app.models.blog import BlogPost, BlogStatus
from app.models.building import (
    BuildingRegisterAncillaryLot,
    BuildingRegisterArea,
    BuildingRegisterFloorDetail,
    BuildingRegisterGeneral,
    BuildingRegisterHeader,
    GisBuildingIntegrated,
)
from app.models.discussion import (
    Discussion,
    DiscussionLike,
    DiscussionReply,
    DiscussionType,
)
from app.models.enums import (
    CollectionStatus,
    PropertyType,
    PublicDataType,
    TransactionType,
)
from app.models.file import FileStorage
from app.models.land import LandAndForestInfo, LandCharacteristic, LandUsePlan
from app.models.lot import AncillaryLand, Lot
from app.models.neighborhood import Neighborhood
from app.models.notification import Notification, NotificationSettings, NotificationType
from app.models.report import Report, ReportCategory, ReportReview, ReportStatus
from app.models.spatial import RoadCenterLine, UseRegionDistrict
from app.models.transaction import OfficialLandPrice, RealEstateRental, RealEstateSale
from app.models.user import AuthProvider, User, UserRole

__all__ = [
    # Base
    "TimestampMixin",
    "PublicDataBase",
    # Enums
    "PropertyType",
    "TransactionType",
    "PublicDataType",
    "CollectionStatus",
    # User
    "User",
    "UserRole",
    "AuthProvider",
    # Neighborhood
    "Neighborhood",
    # Report
    "Report",
    "ReportCategory",
    "ReportReview",
    "ReportStatus",
    # Discussion
    "Discussion",
    "DiscussionReply",
    "DiscussionLike",
    "DiscussionType",
    # Notification
    "Notification",
    "NotificationSettings",
    "NotificationType",
    # Blog
    "BlogPost",
    "BlogStatus",
    # File
    "FileStorage",
    # Lot (필지)
    "Lot",
    "AncillaryLand",
    # Administrative (행정구역)
    "AdministrativeDivision",
    "AdministrativeEmd",
    # Land (토지)
    "LandCharacteristic",
    "LandUsePlan",
    "LandAndForestInfo",
    # Building (건물)
    "BuildingRegisterHeader",
    "BuildingRegisterGeneral",
    "BuildingRegisterFloorDetail",
    "BuildingRegisterArea",
    "BuildingRegisterAncillaryLot",
    "GisBuildingIntegrated",
    # Transaction (실거래가/공시지가)
    "OfficialLandPrice",
    "RealEstateSale",
    "RealEstateRental",
    # Spatial (GIS)
    "RoadCenterLine",
    "UseRegionDistrict",
]
