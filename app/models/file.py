"""File storage model for uploaded files."""

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field

from app.models.base import TimestampMixin


class FileStorage(TimestampMixin, table=True):
    """File storage record for S3 uploads."""

    __tablename__ = "file_storages"

    id: int | None = Field(default=None, primary_key=True)
    file_name: str = Field(max_length=255)
    original_name: str = Field(max_length=255)
    mime_type: str = Field(max_length=100)
    file_size: int  # bytes

    # S3 details
    s3_key: str = Field(max_length=500)
    s3_bucket: str = Field(max_length=100)
    s3_url: str = Field(max_length=1000)

    # Metadata
    uploaded_by: str = Field(foreign_key="users.id", max_length=255, ondelete="CASCADE")
    description: str | None = Field(default=None)
    alt_text: str | None = Field(default=None, max_length=255)
    tags: list | None = Field(default=None, sa_column=Column(JSON))

    # Stats
    download_count: int = Field(default=0)
    is_public: bool = Field(default=True)
