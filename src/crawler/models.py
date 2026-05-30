from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _parse_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    raise ValueError(f"{field_name} 必须是布尔值 true 或 false。")


@dataclass(frozen=True)
class CrawlerConfig:
    user_agent: str
    timeout_seconds: float
    max_retries: int
    retry_backoff_seconds: float
    request_interval_seconds: float
    respect_robots_txt: bool
    max_urls_per_run: int
    output_raw_path: str
    output_products_path: str
    output_report_path: str
    log_path: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CrawlerConfig":
        required_fields = [
            "user_agent",
            "timeout_seconds",
            "max_retries",
            "retry_backoff_seconds",
            "request_interval_seconds",
            "respect_robots_txt",
            "max_urls_per_run",
            "output_raw_path",
            "output_products_path",
            "output_report_path",
            "log_path",
        ]
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise ValueError(f"crawler_config 缺少字段：{', '.join(missing)}")

        config = cls(
            user_agent=str(data["user_agent"]).strip(),
            timeout_seconds=float(data["timeout_seconds"]),
            max_retries=int(data["max_retries"]),
            retry_backoff_seconds=float(data["retry_backoff_seconds"]),
            request_interval_seconds=float(data["request_interval_seconds"]),
            respect_robots_txt=_parse_bool(data["respect_robots_txt"], "respect_robots_txt"),
            max_urls_per_run=int(data["max_urls_per_run"]),
            output_raw_path=str(data["output_raw_path"]),
            output_products_path=str(data["output_products_path"]),
            output_report_path=str(data["output_report_path"]),
            log_path=str(data["log_path"]),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not self.user_agent:
            raise ValueError("user_agent 不能为空。")
        if self.timeout_seconds < 10:
            raise ValueError("timeout_seconds 必须 >= 10。")
        if self.max_retries < 0:
            raise ValueError("max_retries 不能小于 0。")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds 不能小于 0。")
        if self.request_interval_seconds < 2:
            raise ValueError("request_interval_seconds 必须 >= 2。")
        if self.max_urls_per_run <= 0:
            raise ValueError("max_urls_per_run 必须大于 0。")
        if self.max_urls_per_run > 20:
            raise ValueError("max_urls_per_run 必须 <= 20。")
        if self.respect_robots_txt is not True:
            raise ValueError("respect_robots_txt 必须为 true。")
        empty_paths = [
            field
            for field in ["output_raw_path", "output_products_path", "output_report_path", "log_path"]
            if not str(getattr(self, field)).strip()
        ]
        if empty_paths:
            raise ValueError(f"输出路径不能为空：{', '.join(empty_paths)}")

    def output_paths(self) -> dict[str, str]:
        return {
            "raw": self.output_raw_path,
            "products": self.output_products_path,
            "report": self.output_report_path,
            "log": self.log_path,
        }


@dataclass(frozen=True)
class SeedUrl:
    url: str
    source_name: str
    category_hint: str
    note: str

    def to_dict(self) -> dict[str, str]:
        return {
            "url": self.url,
            "source_name": self.source_name,
            "category_hint": self.category_hint,
            "note": self.note,
        }


@dataclass(frozen=True)
class RobotsDecision:
    url: str
    allowed: bool
    reason: str
    robots_url: str


@dataclass(frozen=True)
class FetchResult:
    url: str
    source_name: str
    ok: bool
    status_code: int | None
    final_url: str
    content_type: str
    text: str
    error_type: str
    error_message: str
    attempts: int
    elapsed_seconds: float

    def to_raw_record(self) -> dict[str, Any]:
        html_excerpt = self.text[:4000] if self.text else ""
        return {
            "url": self.url,
            "source_name": self.source_name,
            "ok": self.ok,
            "status_code": self.status_code,
            "final_url": self.final_url,
            "content_type": self.content_type,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "attempts": self.attempts,
            "elapsed_seconds": self.elapsed_seconds,
            "html_excerpt": html_excerpt,
        }


def resolve_project_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return Path(__file__).resolve().parents[2] / candidate
