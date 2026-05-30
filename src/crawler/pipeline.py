from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.crawler.deduper import dedupe_products
from src.crawler.fetcher import ProductFetcher
from src.crawler.logging_utils import setup_crawler_logger, write_json
from src.crawler.models import CrawlerConfig, resolve_project_path
from src.crawler.normalizer import normalize_crawler_products
from src.crawler.parser import parse_product_page
from src.crawler.robots_checker import RobotsChecker
from src.crawler.seed_loader import load_seed_urls


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_crawler_config(config_path: str | Path) -> CrawlerConfig:
    path = resolve_project_path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"采集配置不存在：{path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"采集配置 JSON 格式错误：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("采集配置 JSON 顶层必须是对象。")
    return CrawlerConfig.from_dict(data)


def _make_report(config: CrawlerConfig, total_url_count: int) -> dict[str, Any]:
    return {
        "started_at": _utc_now(),
        "finished_at": "",
        "total_url_count": total_url_count,
        "valid_url_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "skipped_count": 0,
        "robots_restricted_count": 0,
        "http_error_count": 0,
        "parse_failure_count": 0,
        "missing_field_count": 0,
        "dedupe_before_count": 0,
        "dedupe_after_count": 0,
        "manual_review_items": [],
        "invalid_seed_entries": [],
        "skipped_items": [],
        "failures": [],
        "http_errors": [],
        "parse_failures": [],
        "field_missing_items": [],
        "dedupe": {},
        "output_paths": config.output_paths(),
        "notice": "采集结果和推荐结果仅作为采购辅助候选，需人工复核，不是最终采购结论。",
    }


def run_crawler(
    config_path: str | Path = "config/crawler_config.json",
    seed_path: str | Path = "data/seed_urls.json",
) -> dict[str, Any]:
    config = load_crawler_config(config_path)
    resolved_output_paths = {name: resolve_project_path(path) for name, path in config.output_paths().items()}
    logger = setup_crawler_logger(resolved_output_paths["log"])
    logger.info("crawler started")

    seed_file_path = resolve_project_path(seed_path)
    seed_count = 0
    if seed_file_path.exists():
        try:
            seed_data = json.loads(seed_file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            seed_data = []
        if isinstance(seed_data, list):
            seed_count = len(seed_data)

    report = _make_report(config, total_url_count=seed_count)
    raw_records: list[dict[str, Any]] = []
    parsed_products: list[dict[str, Any]] = []

    try:
        seeds, invalid_entries = load_seed_urls(seed_file_path)
        report["invalid_seed_entries"] = invalid_entries
        report["valid_url_count"] = len(seeds)
        logger.info("loaded seeds: valid=%s invalid=%s", len(seeds), len(invalid_entries))

        selected_seeds = seeds[: config.max_urls_per_run]
        for skipped_seed in seeds[config.max_urls_per_run :]:
            report["skipped_count"] += 1
            report["skipped_items"].append(
                {
                    "url": skipped_seed.url,
                    "reason": "超过 max_urls_per_run，已跳过。",
                }
            )

        robots_checker = RobotsChecker(config.user_agent, config.respect_robots_txt, logger=logger)
        fetcher = ProductFetcher(config, logger=logger)

        for seed in selected_seeds:
            logger.info("processing seed url=%s source=%s", seed.url, seed.source_name)
            robots_decision = robots_checker.can_fetch(seed)
            if not robots_decision.allowed:
                report["skipped_count"] += 1
                report["robots_restricted_count"] += 1
                report["skipped_items"].append(
                    {
                        "url": seed.url,
                        "reason": robots_decision.reason,
                        "robots_url": robots_decision.robots_url,
                    }
                )
                logger.info("robots disallowed url=%s robots=%s", seed.url, robots_decision.robots_url)
                continue

            fetch_result = fetcher.fetch(seed)
            raw_record = fetch_result.to_raw_record()
            raw_record["robots"] = {
                "allowed": robots_decision.allowed,
                "reason": robots_decision.reason,
                "robots_url": robots_decision.robots_url,
            }
            raw_records.append(raw_record)

            if not fetch_result.ok:
                report["failure_count"] += 1
                failure = {
                    "url": seed.url,
                    "status_code": fetch_result.status_code,
                    "error_type": fetch_result.error_type,
                    "error_message": fetch_result.error_message,
                }
                report["failures"].append(failure)
                if fetch_result.error_type == "http_error":
                    report["http_error_count"] += 1
                    report["http_errors"].append(failure)
                logger.info("fetch failed url=%s error=%s", seed.url, fetch_result.error_type)
                continue

            parsed = parse_product_page(fetch_result.text, seed, final_url=fetch_result.final_url)
            raw_record["parsed_summary"] = {
                "title": parsed.get("title", ""),
                "price": parsed.get("price", ""),
                "missing_fields": parsed.get("missing_fields", []),
                "parse_success": parsed.get("parse_success", False),
            }
            if not parsed.get("parse_success"):
                report["failure_count"] += 1
                report["parse_failure_count"] += 1
                report["parse_failures"].append({"url": seed.url, "reason": parsed.get("parse_error", "")})
                logger.info("parse failed url=%s", seed.url)
                continue

            report["success_count"] += 1
            missing_fields = parsed.get("missing_fields", [])
            if missing_fields:
                report["missing_field_count"] += len(missing_fields)
                missing_item = {"url": seed.url, "title": parsed.get("title", ""), "missing_fields": missing_fields}
                report["field_missing_items"].append(missing_item)
                report["manual_review_items"].append(missing_item)
            parsed_products.append(parsed)

        normalized_products = normalize_crawler_products(parsed_products)
        deduped_products, dedupe_report = dedupe_products(normalized_products)
        report["dedupe"] = dedupe_report
        report["dedupe_before_count"] = dedupe_report["before_count"]
        report["dedupe_after_count"] = dedupe_report["after_count"]
        report["finished_at"] = _utc_now()

        write_json(resolved_output_paths["raw"], raw_records)
        write_json(resolved_output_paths["products"], deduped_products)
        write_json(resolved_output_paths["report"], report)
        logger.info("crawler finished products=%s report=%s", len(deduped_products), resolved_output_paths["report"])
        return report
    except Exception as exc:
        logger.exception("crawler crashed: %s", exc)
        report["finished_at"] = _utc_now()
        report["failure_count"] += 1
        report["failures"].append({"url": "", "error_type": "crawler_exception", "error_message": str(exc)})
        write_json(resolved_output_paths["raw"], raw_records)
        write_json(resolved_output_paths["products"], [])
        write_json(resolved_output_paths["report"], report)
        raise
