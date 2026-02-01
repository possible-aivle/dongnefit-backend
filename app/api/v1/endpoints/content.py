"""Content generation endpoints."""

from fastapi import APIRouter

from app.schemas.content import ContentRequest, ContentResponse
from app.services.content.generator import ContentGenerator

router = APIRouter()


@router.post("/generate", response_model=ContentResponse)
async def generate_content(request: ContentRequest) -> ContentResponse:
    """Generate real estate content in markdown format."""
    generator = ContentGenerator()
    return await generator.generate(request)


@router.post("/generate-with-image")
async def generate_content_with_image(request: ContentRequest) -> dict:
    """Generate real estate content with image."""
    generator = ContentGenerator()
    result = await generator.generate_with_image(request)
    return result
