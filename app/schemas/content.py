"""Content generation schemas."""

from enum import Enum

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """Types of real estate content."""

    PROPERTY_LISTING = "property_listing"
    NEIGHBORHOOD_GUIDE = "neighborhood_guide"
    MARKET_ANALYSIS = "market_analysis"
    INVESTMENT_INSIGHT = "investment_insight"


class ContentRequest(BaseModel):
    """Content generation request."""

    content_type: ContentType = Field(..., description="Type of content to generate")
    location: str = Field(..., description="Location or address")
    keywords: list[str] = Field(default_factory=list, description="Additional keywords")
    include_image: bool = Field(False, description="Whether to generate image")
    additional_context: str | None = Field(None, description="Additional context")


class ContentResponse(BaseModel):
    """Content generation response."""

    title: str = Field(..., description="Content title")
    content: str = Field(..., description="Generated content in markdown format")
    summary: str = Field(..., description="Brief summary")
    keywords: list[str] = Field(default_factory=list, description="Extracted keywords")
    image_url: str | None = Field(None, description="Generated image URL if requested")
