# 阶段 9 计划：客户指定数据源适配与人工复核闭环 v1

## 1. 阶段目标

阶段 9 的目标是建设客户指定数据源适配与人工复核闭环 v1，让客户提供的数据源更容易接入、采集结果更容易复核、推荐依据更容易解释、Word 输出继续保持可交付。

本阶段不是复杂电商平台攻坚，不承诺万能采集能力。所有无法确认的信息必须进入“需人工复核”。

## 2. 安全边界

1. 不绕登录、验证码或平台风控。
2. 不偷 Cookie。
3. 不使用代理池规避封禁。
4. 不抓个人信息。
5. 不自动下单。
6. 不把采集结果或推荐结果称为最终采购结论。
7. 不默认接淘宝、京东、1688、得物等复杂平台。
8. 所有无法确认的信息必须标记“需人工复核”。

## 3. 允许修改文件

1. `STAGE9_PLAN.md`
2. `TASKS.md`
3. `main.py`
4. `src/crawler/pipeline.py`
5. `src/crawler/review.py`
6. `src/crawler/adapters/*`
7. `tests/test_stage9_adapters.py`
8. `tests/test_stage8_crawler.py`

## 4. 禁止修改文件

1. `app.py`
2. `src/doc_writer.py` 的旧接口
3. `src/response_builder.py` 的旧接口
4. `src/product_loader.py` 的旧接口
5. `src/product_ranker.py` 的旧接口
6. 阶段 1-8.1 验收总结文件

## 5. 输入与输出

输入：

1. 客户提供的公开 URL 列表：`data/seed_urls.json`
2. 客户手动提供的商品 JSON
3. 客户手动提供的商品 CSV
4. 阶段 8 已有采集配置：`config/crawler_config.json`
5. 阶段 1-7 已有 Word 模板与本地样例商品

输出：

1. `outputs/crawler_products.json`
2. `outputs/crawler_report.json`
3. `outputs/manual_review_items.json`
4. `outputs/ranked_products.json`
5. `outputs/responses.json`
6. `outputs/recommendation_result.docx`

## 6. 模块拆分

### 6.1 适配器接口

`src/crawler/adapters/base.py` 定义统一接口：

1. `load_candidates()` 返回统一商品候选列表。
2. 适配器输出可继续进入 `normalize_products`、`rank_products` 和 Word 写回流程。
3. 适配器只保留客户或公开页面可见字段，不编造价格、尺寸、材质、服务或来源。

### 6.2 静态公开页面适配器

`src/crawler/adapters/static_page_adapter.py` 复用阶段 8 的公开 URL 页面采集能力。

它继续遵守阶段 8 的 robots、限速、超时、重试和报告边界，不绕登录、不处理验证码、不规避平台风控。

### 6.3 手动 JSON 适配器

`src/crawler/adapters/manual_json_adapter.py` 支持客户手动提供商品 JSON。

支持 JSON 顶层为数组，或包含 `products` 数组的对象。

### 6.4 手动 CSV 适配器

`src/crawler/adapters/manual_csv_adapter.py` 支持客户手动提供商品 CSV。

CSV 使用表头映射字段，允许常见中文表头，例如“商品名称”“价格”“来源”“链接”“规格参数”“安装服务”。

### 6.5 人工复核清单

`src/crawler/review.py` 根据 `crawler_products.json` 或适配器输出生成 `outputs/manual_review_items.json`。

复核项至少包含：

1. `title`
2. `url`
3. `source`
4. `missing_fields`
5. `manual_review_required`
6. `evidence_text`
7. `risk_reason`
8. `suggested_action`

## 7. 人工复核规则

以下情况必须进入人工复核：

1. 缺价格。
2. 缺尺寸。
3. 缺材质。
4. 缺安装服务。
5. 缺明确来源。
6. 解析证据不足。
7. 上游 parser 或适配器已标记 `manual_review_required`。
8. 页面解析失败或标题为空。

人工复核清单只记录缺失与风险，不补猜字段。

## 8. crawler_report 摘要增强

`crawler_report.json` 增加面向客户阅读的 `summary` 字段，至少包含：

1. 本次采集 URL 数
2. 成功商品数
3. 失败 URL 数
4. 跳过 URL 数
5. 需人工复核商品数
6. 主要失败原因
7. 输出文件路径
8. 免责声明：结果为采购辅助候选，非最终采购结论

## 9. main.py 接入原则

1. 不破坏现有 `run_pipeline` 调用。
2. 保持 `crawler_products.json` 优先、`sample_products.json` 回退逻辑。
3. 如果 `outputs/manual_review_items.json` 存在，在返回结果中增加 `manual_review_path`。
4. 不修改 `doc_writer.py` 旧接口。

## 10. 验收命令

```bash
python -m unittest discover tests
python -m src.product_fetcher
python main.py
python -m json.tool outputs/crawler_report.json
python -m json.tool outputs/manual_review_items.json
python -m json.tool outputs/ranked_products.json
python -m json.tool outputs/responses.json
```

## 11. 残余风险

1. 客户手动 JSON/CSV 的字段命名可能超出当前表头映射，需要人工补充映射。
2. 静态页面解析仍依赖公开页面结构，复杂前端渲染页面可能无法提取完整信息。
3. 材质、尺寸和安装服务的识别依赖字段和文本证据，不能替代人工合同或采购确认。
4. 默认不接复杂平台，不处理登录态、验证码、反爬或动态接口。

## 12. 不做事项

1. 不接入淘宝、京东、1688、得物等复杂平台默认适配器。
2. 不做账号登录、Cookie 导入、验证码处理或代理池。
3. 不做自动下单或库存承诺。
4. 不把推荐结果写成最终采购结论。
5. 不重构阶段 1-8.1 已验收旧接口。
