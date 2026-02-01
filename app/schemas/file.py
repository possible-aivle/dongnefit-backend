"""File storage schemas."""

from pydantic import BaseModel

from app.schemas.base import PaginationParams, TimestampSchema

# === Request Schemas ===


class FileUploadMeta(BaseModel):
    """Metadata for file upload."""

    description: str | None = None
    alt_text: str | None = None
    tags: list[str] | None = None
    is_public: bool = True


class FileUpdate(BaseModel):
    """Schema for updating file metadata."""

    description: str | None = None
    alt_text: str | None = None
    tags: list[str] | None = None
    is_public: bool | None = None


class FileQuery(PaginationParams):
    """Query parameters for listing files."""

    search: str | None = None
    mime_type: str | None = None
    uploaded_by: str | None = None
    is_public: bool | None = None
    sort_by: str = "newest"  # newest, name, size


# === Response Schemas ===


class FileResponse(TimestampSchema):
    """File response."""

    id: int
    file_name: str
    original_name: str
    mime_type: str
    file_size: int
    s3_url: str
    uploaded_by: str
    description: str | None
    alt_text: str | None
    tags: list[str] | None
    download_count: int
    is_public: bool


class FileUploadResponse(BaseModel):
    """Response after file upload."""

    id: int
    file_name: str
    s3_url: str
    mime_type: str
    file_size: int


class PresignedUrlResponse(BaseModel):
    """Presigned URL for direct upload."""

    upload_url: str
    file_key: str
    expires_in: int
