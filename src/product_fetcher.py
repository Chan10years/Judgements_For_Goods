from __future__ import annotations

from src.crawler.pipeline import run_crawler


def main() -> int:
    try:
        report = run_crawler()
    except Exception as exc:
        print(f"商品采集流程失败：{exc}")
        return 1

    print("商品采集流程完成。")
    print(f"总 URL 数：{report['total_url_count']}")
    print(f"有效 URL 数：{report['valid_url_count']}")
    print(f"成功数：{report['success_count']}")
    print(f"失败数：{report['failure_count']}")
    print(f"跳过数：{report['skipped_count']}")
    print(f"去重前数量：{report['dedupe_before_count']}")
    print(f"去重后数量：{report['dedupe_after_count']}")
    print(f"报告路径：{report['output_paths']['report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
