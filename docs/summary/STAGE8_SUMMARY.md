# 阶段 8 总结：生产级商品数据采集子系统 v1 与 8.1 修复硬化

## 1. 阶段目标

阶段 8 的目标是建设生产级商品数据采集子系统 v1，形成合规、可配置、可限速、可追踪、可兜底的采集底座。

本阶段不直接攻克复杂平台，不绕过登录、验证码、平台风控，不偷 Cookie，不使用代理池规避封禁，不抓取个人信息，不自动下单，也不把采集结果或推荐结果称为最终采购结论。

阶段 8.1 在阶段 8 已实现的基础上做修复硬化，目标是让采集底座达到客户交付验收强度。

## 2. 新增和修改文件

新增文件：

- `STAGE8_PLAN.md`
- `STAGE8_SUMMARY.md`
- `config/crawler_config.json`
- `data/seed_urls.json`
- `src/product_fetcher.py`
- `src/crawler/__init__.py`
- `src/crawler/models.py`
- `src/crawler/seed_loader.py`
- `src/crawler/robots_checker.py`
- `src/crawler/fetcher.py`
- `src/crawler/parser.py`
- `src/crawler/normalizer.py`
- `src/crawler/deduper.py`
- `src/crawler/pipeline.py`
- `src/crawler/logging_utils.py`
- `tests/test_stage8_crawler.py`

修改文件：

- `main.py`
- `requirements.txt`
- `TASKS.md`

运行产物：

- `outputs/crawler_raw.json`
- `outputs/crawler_products.json`
- `outputs/crawler_report.json`
- `logs/crawler_run.log`
- `outputs/ranked_products.json`
- `outputs/responses.json`
- `outputs/recommendation_result.docx`

## 3. 阶段 8 完成功能

已完成可配置采集配置：

- `config/crawler_config.json` 包含 User-Agent、超时、重试、退避、请求间隔、robots 开关、单次最大 URL 数、输出路径和日志路径。
- 默认配置为保守配置：`timeout_seconds = 10`、`request_interval_seconds = 2`、`max_urls_per_run = 20`、`respect_robots_txt = true`。

已完成 seed URL 读取：

- `data/seed_urls.json` 默认为空数组，不预置淘宝、京东、1688、得物等复杂平台 URL。
- `seed_loader.py` 支持 seed URL 格式校验、必填字段校验和重复 URL 去重。
- 无效 URL 和重复 URL 可进入报告。

已完成 robots 检查：

- `robots_checker.py` 使用 `urllib.robotparser`。
- 当 robots 不允许时跳过，并记录原因。
- 当配置要求尊重 robots 时，不提供绕过开关。

已完成 fetcher：

- `fetcher.py` 使用 `requests`。
- 设置 User-Agent、timeout、重试、退避和请求间隔。
- 记录 HTTP 错误、timeout、网络异常。
- 识别疑似登录、验证码、访问受限页面，只记录失败，不绕过。

已完成 parser：

- `parser.py` 使用 BeautifulSoup 解析页面。
- 提取 `title`、meta description、h1、正文、价格、规格文本、服务文本和 evidence。
- 缺失字段留空，不编造价格、品牌、颜色、材质、尺寸或安装服务。
- `raw_text` 和 `evidence_text` 控制在约 2000 字。

已完成 normalizer：

- `normalizer.py` 调用现有 `normalize_products`。
- 输出可继续被 `rank_products(products, requirements)` 接收。
- 保留 evidence、missing_fields、manual_review_required 等采集字段。

已完成 deduper：

- `deduper.py` 优先按 URL 去重。
- URL 为空时按 `title + price + dimensions` 或 `title + price + specs_text 摘要` 弱去重。
- 报告包含去重前数量、去重后数量、移除数量和重复原因。

已完成 pipeline 与命令入口：

- `pipeline.py` 实现 `run_crawler(config_path="config/crawler_config.json", seed_path="data/seed_urls.json")`。
- `src/product_fetcher.py` 支持 `python -m src.product_fetcher`。
- 默认输出 `crawler_raw.json`、`crawler_products.json`、`crawler_report.json` 和 `crawler_run.log`。

已完成主流程接入：

- `main.py` 优先读取 `outputs/crawler_products.json`。
- 当采集产物不存在、为空、JSON 错误或没有可用商品时，回退 `data/sample_products.json`。
- 主流程继续生成 `ranked_products.json`、`responses.json` 和 `recommendation_result.docx`。

## 4. 阶段 8.1 修复硬化

阶段 8.1 完成以下硬化：

- `CrawlerConfig.validate()` 强制生产保守校验：超时不低于 10 秒、请求间隔不低于 2 秒、单次 URL 不超过 20、必须尊重 robots。
- `respect_robots_txt` 必须为 true，不提供 dev mode 或绕过开关。
- parser 成功条件收紧为至少存在 `title`；只有普通正文但无标题的页面会记为解析失败。
- parser 对缺失的 price、specs_text、service_text 留空并进入人工复核，不编造字段。
- deduper 增强 URL 为空时的规格摘要弱去重，重复原因记录为 `duplicate_title_price_specs`。
- `main.py` 对 `crawler_products.json` 增强有效性判断，只有至少一个商品 dict 同时具备 title 和 url/source/platform 之一时才使用采集产物。
- `tests/test_stage8_crawler.py` 增加配置、parser、deduper、main 回退和 mock pipeline 覆盖。

## 5. 验收命令与结果

已运行以下命令：

```powershell
python -m json.tool config/crawler_config.json
python -m json.tool data/seed_urls.json
python -m unittest discover tests
python -m src.product_fetcher
python main.py
python -m json.tool outputs/crawler_raw.json
python -m json.tool outputs/crawler_products.json
python -m json.tool outputs/crawler_report.json
python -m json.tool outputs/ranked_products.json
python -m json.tool outputs/responses.json
```

结果：

- 配置 JSON 校验通过。
- seed URL JSON 校验通过。
- unittest 全量通过：16 个测试 OK。
- `python -m src.product_fetcher` 运行成功。
- `python main.py` 运行成功。
- 采集 raw/products/report JSON 均可解析。
- ranked_products/responses JSON 均可解析。
- `outputs/recommendation_result.docx` 已生成。

## 6. 当前采集报告结果

默认 `data/seed_urls.json` 为空，因此本轮采集结果为安全空跑：

- 总 URL 数：0
- 有效 URL 数：0
- 成功数：0
- 失败数：0
- 跳过数：0
- robots 限制数：0
- HTTP 错误数：0
- 解析失败数：0
- 字段缺失数：0
- 去重前数量：0
- 去重后数量：0

`crawler_report.json` 已明确提示：采集结果和推荐结果仅作为采购辅助候选，需人工复核，不是最终采购结论。

## 7. 阶段 1-7 回归情况

阶段 1-7 主流程仍通过。

验证点：

- Word 需求解析仍能输出 13 条需求。
- 本地样例商品仍能读取并标准化。
- 规则评分排序仍能生成 `ranked_products.json`。
- Top 3 与规则响应仍能生成 `responses.json`。
- Word 写回仍能生成 `outputs/recommendation_result.docx`。
- `write_responses(input_path, responses, output_path)` 和 `write_responses(..., summary_products=top_products)` 旧接口未破坏。
- `load_products(path)`、`load_products_json(path)`、`normalize_products(products)`、`rank_products(products, requirements)` 旧接口未破坏。

## 8. 阶段边界确认

阶段 8 和 8.1 未做以下事项：

- 未接入淘宝、京东、1688、得物等复杂平台。
- 未绕过登录。
- 未绕过验证码。
- 未绕过平台风控。
- 未偷用 Cookie。
- 未使用代理池规避封禁。
- 未抓取个人信息。
- 未自动下单。
- 未把采集结果或推荐结果称为最终采购结论。
- 未进入阶段 9 客户指定数据源适配器。

## 9. 客户交付验收口径

阶段 8 当前交付对象是“采集底座 v1”，不是任意真实平台适配器。

验收口径：

- 通过保守配置校验。
- 通过 seed URL 校验与去重测试。
- 通过 parser 不编造字段测试。
- 通过 robots、fetcher、parser、normalizer、deduper、report/log 的 mock pipeline 测试。
- 通过采集为空或无效时 `main.py` 回退本地样例商品测试。
- 通过阶段 1-7 端到端主流程回归测试。

真实客户 URL 采集属于后续客户数据源适配和授权验证范围，需要客户提供公开 URL、授权说明、页面样例和字段验收标准，不承诺万能平台采集。

## 10. 残余风险

- 当前默认 seed 为空，尚未对真实客户 URL 做站点级适配验证。
- 通用 parser 只能抽取公开页面显式文本，无法保证所有页面结构都能完整解析。
- 外部站点 robots、登录、验证码、风控或页面结构变化会导致跳过或失败。
- 价格、服务、规格等字段依赖页面公开文本，缺失时必须人工复核。
- 规则评分和 Word 响应仍为采购辅助，不替代人工采购判断。

## 11. 最终结论

阶段 8 已完成生产级商品数据采集底座 v1。

阶段 8.1 已完成交付前修复硬化。

验收结论：通过。

当前系统具备配置、seed URL 校验、robots 检查、限速请求、页面解析、标准化、去重、报告日志、命令入口、主流程采集优先和本地样例回退能力。阶段 8 当前结果是合规采集底座，不是复杂平台适配器，不是最终采购结论。

下一阶段建议进入阶段 9：客户指定数据源适配器。在进入阶段 9 前，应先确认客户授权范围、公开 URL 列表、robots 规则、页面样例和字段验收标准。
