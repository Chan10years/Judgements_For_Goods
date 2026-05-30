# 阶段 8 计划：生产级商品数据采集子系统 v1

## 1. 阶段目标

阶段 8 建设可配置、可限速、可追踪、可兜底的商品数据采集底座。系统读取客户提供的公开 URL，按配置检查 robots、限速请求页面、解析商品文本、标准化字段、去重清洗，并输出采集原始记录、标准化商品、采集报告和运行日志。

阶段 8 不直接攻克复杂平台，不绕过登录、验证码、风控、Cookie 或授权限制，不抓取个人信息，不自动下单，不把采集或推荐结果称为最终采购结论。

## 2. 输入与输出

输入：

- `config/crawler_config.json`
- `data/seed_urls.json`
- 客户明确提供且可公开访问的 URL

输出：

- `outputs/crawler_raw.json`
- `outputs/crawler_products.json`
- `outputs/crawler_report.json`
- `logs/crawler_run.log`

主流程接入：

- `main.py` 优先读取 `outputs/crawler_products.json`
- 当该文件不存在、为空或不是有效商品数组时，回退 `data/sample_products.json`
- 继续生成 `outputs/ranked_products.json`、`outputs/responses.json`、`outputs/recommendation_result.docx`

## 3. 模块边界

- `seed_loader.py`：读取、校验、去重 seed URL；无效或重复条目进入报告。
- `robots_checker.py`：使用 `urllib.robotparser` 检查 robots；被拒绝时跳过并记录原因。
- `fetcher.py`：使用 `requests`，执行 User-Agent、timeout、重试、退避和请求间隔；记录 HTTP 和网络错误。
- `parser.py`：使用 BeautifulSoup 提取标题、描述、h1、正文、价格、规格、服务文本、证据文本；缺失字段留空。
- `normalizer.py`：调用现有 `normalize_products`，再保留采集证据和人工复核标记。
- `deduper.py`：优先按 URL 去重；无 URL 时按 `title + price + dimensions` 或 `title + price + specs_text 摘要` 弱去重。
- `pipeline.py`：串联配置、seed、robots、fetch、parse、normalize、dedupe、报告和日志。
- `src/product_fetcher.py`：提供 `python -m src.product_fetcher` 命令入口。

## 4. 默认配置原则

- `respect_robots_txt` 默认为 `true`
- `timeout_seconds` 不低于 10
- `request_interval_seconds` 不低于 2
- `max_urls_per_run` 不高于 20
- 配置校验必须强制执行上述保守值，不提供 dev mode 或绕过开关
- 默认 seed 文件不内置淘宝、京东、1688、得物等复杂平台 URL

## 5. 失败兜底

- robots 不允许：跳过 URL，写报告和日志。
- 登录页、验证码页、访问受限页：只记录失败，不绕过。
- HTTP 401、403、404、429、timeout、网络异常：记录失败，不伪造商品。
- 页面字段缺失：字段留空，进入人工复核项。
- 采集结果为空：`main.py` 自动回退本地 `data/sample_products.json`，保持推荐和 Word 写回流程可运行。

## 6. 验收命令

```powershell
python -m json.tool config/crawler_config.json
python -m json.tool data/seed_urls.json
python -m src.product_fetcher
python -m json.tool outputs/crawler_raw.json
python -m json.tool outputs/crawler_products.json
python -m json.tool outputs/crawler_report.json
python main.py
python -m json.tool outputs/ranked_products.json
python -m json.tool outputs/responses.json
python -m unittest discover tests
```

## 7. 阶段完成标准

- 所有阶段 8 新增模块可导入。
- 默认配置符合保守限制。
- seed URL 校验和去重可测试。
- parser 不编造价格、品牌、颜色、材质、尺寸或安装服务。
- deduper 记录去重前后数量和原因。
- pipeline 生成 raw、products、report、log。
- `main.py` 保留阶段 5-7 端到端输出，并实现采集产物优先、本地样例回退。

## 8. 阶段 8.1 修复硬化

阶段 8.1 不新增大功能，不进入阶段 9，仅对采集底座 v1 做客户交付验收前硬化。

修复内容：

- `CrawlerConfig.validate()` 强制生产级保守配置：`timeout_seconds >= 10`、`request_interval_seconds >= 2`、`max_urls_per_run <= 20`、`respect_robots_txt = true`，并检查重试、退避、User-Agent 和输出路径。
- parser 成功条件收紧为至少存在 `title`；只有普通正文但无标题的页面记为解析失败。价格、规格、服务缺失继续留空，并进入 `missing_fields` 与人工复核项。
- deduper 在 URL 为空时使用 `title + price + dimensions` 或 `title + price + specs_text 摘要` 去重，重复原因记录为 `duplicate_url` 或 `duplicate_title_price_specs`。
- `main.py` 仅在 `crawler_products.json` 包含至少一个可用商品对象时优先使用采集产物；否则回退 `data/sample_products.json`。
- unittest 覆盖配置保守校验、无标题解析失败、不编造字段、弱去重、无效采集产物回退和 mock pipeline 输出。

当前验收口径：

- 阶段 8 当前交付为“采集底座 v1”，通过保守配置、mock 测试、日志报告产物和主流程回退验证。
- 默认 `data/seed_urls.json` 为空，不预置复杂平台 URL。
- 真实客户 URL 采集属于后续客户数据源适配和授权验证范围，不承诺万能平台采集。
