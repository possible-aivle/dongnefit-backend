"""Agent-facing helpers for LAWD (법정동코드)."""

from __future__ import annotations

from app.core.repositories.lawd import LawdRepository


class LawdToolService:
    """Thin wrapper around `LawdRepository` for agent/services usage."""

    def __init__(self, repo: LawdRepository | None = None):
        self.repo = repo or LawdRepository()

    def resolve_code5(self, region_name: str) -> str | None:
        return self.repo.resolve_code5(region_name)

    def search(self, query: str, *, limit: int = 20) -> list[dict]:
        return [
            {
                "lawd_cd": c.lawd_cd,
                "full_name": c.full_name,
                "sido": c.sido,
                "sigungu": c.sigungu,
                "emd": c.emd,
            }
            for c in self.repo.search(query, limit=limit)
        ]
