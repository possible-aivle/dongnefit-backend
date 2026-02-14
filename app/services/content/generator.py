"""Content generator service using LangGraph workflow."""

import httpx

from app.config import settings
from app.core.langgraph.workflow import ContentGenerationWorkflow, ContentState
from app.schemas.content import ContentRequest, ContentResponse
from app.services.content.scraper import RealEstateScraper


class ContentGenerator:
    """Service for generating real estate content."""

    def __init__(self):
        self.workflow = ContentGenerationWorkflow()
        self.scraper = RealEstateScraper()

    async def generate(self, request: ContentRequest) -> ContentResponse:
        """Generate real estate content based on request."""
        # Optionally scrape data
        scraped_data = None
        if request.additional_context and "scrape" in request.additional_context.lower():
            properties = await self.scraper.scrape_naver_real_estate(request.location)
            scraped_data = {
                "properties": [
                    {
                        "name": p.name,
                        "address": p.address,
                        "price": p.price,
                    }
                    for p in properties
                ]
            }

        # Prepare initial state
        initial_state: ContentState = {
            "location": request.location,
            "content_type": request.content_type.value,
            "keywords": request.keywords,
            "additional_context": request.additional_context,
            "scraped_data": scraped_data,
            "research": None,
            "outline": None,
            "draft": None,
            "final_content": None,
            "title": None,
            "summary": None,
        }

        # Run workflow
        result = await self.workflow.run(initial_state)

        return ContentResponse(
            title=result.get("title", ""),
            content=result.get("final_content", ""),
            summary=result.get("summary", ""),
            keywords=request.keywords,
            image_url=None,
        )

    async def generate_with_image(self, request: ContentRequest) -> dict:
        """Generate content with an accompanying image."""
        # Generate text content first
        content_response = await self.generate(request)

        # Generate image using DALL-E or similar
        image_url = await self._generate_image(
            location=request.location,
            content_type=request.content_type.value,
            keywords=request.keywords,
        )

        return {
            "title": content_response.title,
            "content": content_response.content,
            "summary": content_response.summary,
            "keywords": content_response.keywords,
            "image_url": image_url,
        }

    async def _generate_image(
        self,
        location: str,
        content_type: str,
        keywords: list[str],
    ) -> str | None:
        """Generate an image for the content using OpenAI DALL-E."""
        # 이미지 생성 잠시 중단 (요금 절감)
        print("ℹ️ 이미지 생성이 비활성화되어 있습니다.")
        return None

        if not settings.openai_api_key:
            return None

        prompt = f"""
        A modern, professional real estate photograph or illustration of {location} area in Korea.
        Style: Clean, bright, inviting real estate marketing image.
        Content type: {content_type}
        Keywords: {', '.join(keywords)}
        No text or watermarks.
        """

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "dall-e-3",
                        "prompt": prompt,
                        "n": 1,
                        "size": "1024x1024",
                        "quality": "standard",
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["url"]

        except Exception as e:
            print(f"Image generation error: {e}")
            return None
