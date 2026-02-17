import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import aiohttp

API_BASE_URL = "https://support.discord.com/api/v2/help_center/en-us/articles.json"


@dataclass
class HelpCenterArticle:
    article_id: int
    title: str
    html_url: str
    updated_at: str

    @classmethod
    def from_api(cls, payload: Dict[str, Any]) -> "HelpCenterArticle":
        return cls(
            article_id=payload["id"],
            title=payload["title"],
            html_url=payload["html_url"],
            updated_at=payload["updated_at"],
        )

    def updated_datetime(self) -> datetime:
        return datetime.fromisoformat(self.updated_at.replace("Z", "+00:00"))


class DiscordHelpCenterClient:
    def __init__(self, session: aiohttp.ClientSession, logger: logging.Logger):
        self.session = session
        self.logger = logger

    async def _fetch_page(self, page: int, per_page: int = 100) -> Dict[str, Any]:
        retries = 4
        backoff_seconds = 1

        for attempt in range(1, retries + 1):
            try:
                params = {"page": page, "per_page": per_page}
                async with self.session.get(API_BASE_URL, params=params, timeout=20) as response:
                    if response.status == 429:
                        retry_after = float(response.headers.get("Retry-After", "1"))
                        self.logger.warning(
                            "Rate limit na API (429) na página %s. Aguardando %.2fs.", page, retry_after
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    if response.status >= 500:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message="Erro temporário no servidor",
                            headers=response.headers,
                        )

                    response.raise_for_status()
                    return await response.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                if attempt == retries:
                    raise RuntimeError(f"Falha ao obter página {page} após {retries} tentativas") from exc

                self.logger.warning(
                    "Erro ao buscar página %s (tentativa %s/%s): %s. Retry em %ss",
                    page,
                    attempt,
                    retries,
                    exc,
                    backoff_seconds,
                )
                await asyncio.sleep(backoff_seconds)
                backoff_seconds *= 2

        raise RuntimeError(f"Falha inesperada ao obter página {page}")

    async def fetch_all_articles(self) -> List[HelpCenterArticle]:
        first_page = await self._fetch_page(page=1)
        count = first_page.get("count", 0)
        page_count = first_page.get("page_count", 1)
        next_page = first_page.get("next_page")
        articles = [HelpCenterArticle.from_api(a) for a in first_page.get("articles", [])]

        self.logger.info(
            "Página 1 lida. count=%s page_count=%s next_page=%s artigos=%s",
            count,
            page_count,
            next_page,
            len(articles),
        )

        for page in range(2, page_count + 1):
            payload = await self._fetch_page(page=page)
            page_articles = [HelpCenterArticle.from_api(a) for a in payload.get("articles", [])]
            articles.extend(page_articles)
            self.logger.info(
                "Página %s lida. next_page=%s artigos=%s",
                page,
                payload.get("next_page"),
                len(page_articles),
            )

        return articles


def sort_articles_by_updated_desc(articles: List[HelpCenterArticle]) -> List[HelpCenterArticle]:
    return sorted(
        articles,
        key=lambda article: (article.updated_datetime(), article.article_id),
        reverse=True,
    )


def filter_recent_articles(
    articles: List[HelpCenterArticle],
    *,
    recent_minutes: int,
    now_utc: Optional[datetime] = None,
) -> List[HelpCenterArticle]:
    reference_now = now_utc or datetime.now(timezone.utc)
    cutoff = reference_now - timedelta(minutes=recent_minutes)
    recent = [article for article in articles if article.updated_datetime() >= cutoff]
    return sort_articles_by_updated_desc(recent)


def filter_articles_newer_than(
    articles: List[HelpCenterArticle],
    *,
    last_updated_at: Optional[str],
    last_article_id: Optional[int],
) -> List[HelpCenterArticle]:
    if not last_updated_at:
        return []

    last_dt = datetime.fromisoformat(last_updated_at.replace("Z", "+00:00"))
    last_id = last_article_id or 0

    fresh = [
        article
        for article in articles
        if (article.updated_datetime(), article.article_id) > (last_dt, last_id)
    ]
    return sort_articles_by_updated_desc(fresh)
