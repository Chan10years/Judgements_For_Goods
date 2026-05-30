from __future__ import annotations

import logging
import time
from typing import Any

import requests

from src.crawler.models import CrawlerConfig, FetchResult, SeedUrl


RESTRICTED_PAGE_KEYWORDS = [
    "captcha",
    "verify you are human",
    "access denied",
    "forbidden",
    "login",
    "sign in",
    "验证码",
    "登录",
    "访问受限",
    "安全验证",
    "人机验证",
    "请完成验证",
]


class ProductFetcher:
    def __init__(self, config: CrawlerConfig, logger: logging.Logger | None = None) -> None:
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.session = requests.Session()
        self._last_request_at: float | None = None

    def _wait_for_rate_limit(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        wait_seconds = self.config.request_interval_seconds - elapsed
        if wait_seconds > 0:
            time.sleep(wait_seconds)

    def _looks_restricted(self, text: str) -> bool:
        sample = text[:5000].lower()
        return any(keyword.lower() in sample for keyword in RESTRICTED_PAGE_KEYWORDS)

    def fetch(self, seed: SeedUrl | dict[str, Any]) -> FetchResult:
        url = seed.url if isinstance(seed, SeedUrl) else str(seed.get("url", ""))
        source_name = seed.source_name if isinstance(seed, SeedUrl) else str(seed.get("source_name", ""))
        attempts = 0
        started_at = time.monotonic()
        last_error_type = ""
        last_error_message = ""
        status_code: int | None = None
        final_url = url
        content_type = ""
        text = ""

        for attempt in range(1, self.config.max_retries + 2):
            attempts = attempt
            self._wait_for_rate_limit()
            self._last_request_at = time.monotonic()
            try:
                response = self.session.get(
                    url,
                    headers={"User-Agent": self.config.user_agent},
                    timeout=self.config.timeout_seconds,
                )
            except requests.Timeout as exc:
                last_error_type = "timeout"
                last_error_message = str(exc)
                self.logger.warning("timeout fetching %s on attempt %s", url, attempt)
            except requests.RequestException as exc:
                last_error_type = "network_error"
                last_error_message = str(exc)
                self.logger.warning("network error fetching %s on attempt %s: %s", url, attempt, exc)
            else:
                status_code = response.status_code
                final_url = response.url
                content_type = response.headers.get("Content-Type", "")
                response.encoding = response.encoding or response.apparent_encoding
                text = response.text or ""

                if status_code == 200 and self._looks_restricted(text):
                    return FetchResult(
                        url=url,
                        source_name=source_name,
                        ok=False,
                        status_code=status_code,
                        final_url=final_url,
                        content_type=content_type,
                        text="",
                        error_type="access_restricted",
                        error_message="页面疑似登录、验证码或访问受限页，已停止处理。",
                        attempts=attempts,
                        elapsed_seconds=round(time.monotonic() - started_at, 3),
                    )

                if status_code == 200:
                    return FetchResult(
                        url=url,
                        source_name=source_name,
                        ok=True,
                        status_code=status_code,
                        final_url=final_url,
                        content_type=content_type,
                        text=text,
                        error_type="",
                        error_message="",
                        attempts=attempts,
                        elapsed_seconds=round(time.monotonic() - started_at, 3),
                    )

                last_error_type = "http_error"
                last_error_message = f"HTTP {status_code}"
                self.logger.warning("HTTP error fetching %s: %s", url, status_code)
                if status_code in {401, 403, 404, 429} or status_code < 500:
                    break

            if attempt <= self.config.max_retries and self.config.retry_backoff_seconds > 0:
                time.sleep(self.config.retry_backoff_seconds * attempt)

        return FetchResult(
            url=url,
            source_name=source_name,
            ok=False,
            status_code=status_code,
            final_url=final_url,
            content_type=content_type,
            text="",
            error_type=last_error_type or "unknown_error",
            error_message=last_error_message or "请求失败。",
            attempts=attempts,
            elapsed_seconds=round(time.monotonic() - started_at, 3),
        )
