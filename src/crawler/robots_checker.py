from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse, urlunparse
from urllib.robotparser import RobotFileParser

from src.crawler.models import RobotsDecision, SeedUrl


class RobotsChecker:
    def __init__(self, user_agent: str, respect_robots_txt: bool = True, logger: logging.Logger | None = None) -> None:
        self.user_agent = user_agent
        self.respect_robots_txt = respect_robots_txt
        self.logger = logger or logging.getLogger(__name__)
        self._cache: dict[str, RobotFileParser | None] = {}

    def _robots_url(self, url: str) -> str:
        parsed = urlparse(url)
        root = parsed._replace(path="/robots.txt", params="", query="", fragment="")
        return urlunparse(root)

    def can_fetch(self, seed: SeedUrl | dict[str, Any]) -> RobotsDecision:
        url = seed.url if isinstance(seed, SeedUrl) else str(seed.get("url", ""))
        robots_url = self._robots_url(url)
        if not self.respect_robots_txt:
            return RobotsDecision(url=url, allowed=True, reason="robots_check_disabled", robots_url=robots_url)

        if robots_url not in self._cache:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            try:
                parser.read()
            except Exception as exc:
                self.logger.warning("robots check failed for %s: %s", robots_url, exc)
                self._cache[robots_url] = None
            else:
                self._cache[robots_url] = parser

        parser = self._cache.get(robots_url)
        if parser is None:
            return RobotsDecision(
                url=url,
                allowed=True,
                reason="robots_unavailable_allowed_with_log",
                robots_url=robots_url,
            )

        allowed = parser.can_fetch(self.user_agent, url)
        reason = "robots_allowed" if allowed else "robots_disallowed"
        return RobotsDecision(url=url, allowed=allowed, reason=reason, robots_url=robots_url)
