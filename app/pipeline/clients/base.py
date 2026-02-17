"""공통 HTTP 클라이언트 베이스."""

from dataclasses import dataclass, field
from typing import Any

import httpx
from rich.console import Console

console = Console()


@dataclass
class APIResponse:
    """API 응답 래퍼."""

    status_code: int
    data: Any
    total_count: int | None = None
    page: int = 1


@dataclass
class ClientConfig:
    """클라이언트 설정."""

    base_url: str
    api_key: str = ""
    timeout: int = 30
    max_retries: int = 3
    headers: dict[str, str] = field(default_factory=dict)


class BaseClient:
    """공공데이터 API 공통 클라이언트.

    재시도, 레이트리밋, 에러핸들링을 공통으로 처리합니다.
    """

    def __init__(self, config: ClientConfig):
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers=self.config.headers,
            )
        return self._client

    async def get(self, path: str, params: dict[str, Any] | None = None) -> APIResponse:
        """GET 요청 (재시도 포함)."""
        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = await client.get(path, params=params)
                response.raise_for_status()
                return APIResponse(
                    status_code=response.status_code,
                    data=response.json(),
                )
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    console.print(f"  [yellow]레이트리밋 도달, 재시도 {attempt}/{self.config.max_retries}[/]")
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            except httpx.RequestError as e:
                last_error = e
                console.print(f"  [yellow]요청 실패, 재시도 {attempt}/{self.config.max_retries}: {e}[/]")
                import asyncio
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError(f"최대 재시도 횟수 초과: {last_error}")

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
