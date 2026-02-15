"""News search and collection tools."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.core.agent.models import NewsArticle


class NewsSearchService:
    """뉴스 검색 서비스 (네이버 검색 API 기반)."""

    def __init__(self):
        """Initialize news search service."""
        self.client_id = getattr(settings, "naver_client_id", "")
        self.client_secret = getattr(settings, "naver_client_secret", "")
        self.base_url = "https://openapi.naver.com/v1/search/news.json"

    async def search_news(
        self,
        keyword: str,
        display: int = 100,
        days_ago: int = 30,
    ) -> list[NewsArticle]:
        """
        네이버 뉴스 검색 API를 사용하여 기사를 검색합니다.

        Args:
            keyword: 검색 키워드
            display: 검색 결과 개수 (최대 100)
            days_ago: 최근 며칠 이내의 기사만 수집

        Returns:
            검색된 뉴스 기사 목록
        """
        if not self.client_id or not self.client_secret:
            print(
                "[경고] 네이버 API 키가 설정되지 않았습니다. 빈 결과를 반환합니다."
            )
            return []

        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }

        params = {
            "query": keyword,
            "display": min(display, 100),
            "sort": "date",  # 날짜순 정렬
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url, headers=headers, params=params, timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

            articles = []
            cutoff_date = datetime.now() - timedelta(days=days_ago)

            for item in data.get("items", []):
                # HTML 태그 제거
                title = self._remove_html_tags(item["title"])
                description = self._remove_html_tags(item["description"])

                # 날짜 파싱 (네이버 API는 "YYYYMMDD" 형식)
                pub_date_str = item.get("pubDate", "")
                try:
                    pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
                except ValueError:
                    # 파싱 실패 시 현재 시각 사용
                    pub_date = datetime.now()

                # 날짜 필터링
                if pub_date.replace(tzinfo=None) < cutoff_date:
                    continue

                article = NewsArticle(
                    title=title,
                    source="네이버 뉴스",  # API는 개별 언론사 정보 제공 안 함
                    url=item["link"],
                    publish_date=pub_date.replace(tzinfo=None),
                    content=description,  # API는 본문 전체 제공 안 함
                    category=None,
                )
                articles.append(article)

            print(f"[검색] '{keyword}' 키워드로 {len(articles)}개 기사 수집")
            return articles

        except Exception as e:
            print(f"[오류] 뉴스 검색 실패 ({keyword}): {e}")
            return []

    async def search_multiple_keywords(
        self, keywords: list[str], display_per_keyword: int = 20
    ) -> list[NewsArticle]:
        """
        여러 키워드로 동시에 뉴스를 검색합니다.

        Args:
            keywords: 검색 키워드 목록
            display_per_keyword: 키워드당 검색 결과 개수

        Returns:
            모든 검색 결과를 합친 뉴스 목록 (중복 제거)
        """
        tasks = [
            self.search_news(keyword, display=display_per_keyword)
            for keyword in keywords
        ]
        results = await asyncio.gather(*tasks)

        # 결과 합치기 및 중복 제거 (URL 기준)
        all_articles = []
        seen_urls = set()

        for article_list in results:
            for article in article_list:
                if article.url not in seen_urls:
                    all_articles.append(article)
                    seen_urls.add(article.url)

        print(f"[수집 완료] 총 {len(all_articles)}개 고유 기사 수집")
        return all_articles

    def _remove_html_tags(self, text: str) -> str:
        """HTML 태그 제거."""
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text()


class WebCrawler:
    """웹 크롤러 (기사 본문 추출용)."""

    async def fetch_article_content(self, url: str) -> Optional[str]:
        """
        기사 URL에서 본문을 추출합니다.

        Args:
            url: 기사 URL

        Returns:
            추출된 본문 (실패 시 None)
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0, follow_redirects=True)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 일반적인 뉴스 사이트의 본문 태그 시도
            # (실제로는 언론사별로 다르므로 휴리스틱 적용)
            content = None

            # 네이버 뉴스
            if "news.naver.com" in url:
                article_body = soup.find("div", {"id": "dic_area"})
                if article_body:
                    content = article_body.get_text(strip=True)

            # 일반 패턴
            if not content:
                # <article> 태그 시도
                article_tag = soup.find("article")
                if article_tag:
                    content = article_tag.get_text(strip=True)

            # 실패 시 None 반환
            return content

        except Exception as e:
            print(f"[크롤링 오류] {url}: {e}")
            return None
