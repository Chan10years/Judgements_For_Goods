# 阶段10总结：客户复核回填闭环

## 阶段目标

阶段10目标是读取客户或人工补齐后的复核结果，生成：

1. `outputs/reviewed_products.json`
2. `outputs/review_report.json`

并让已复核商品按优先级重新进入推荐排序与 Word 写回流程。

本阶段只处理人工复核回填闭环，不绕登录、验证码或风控，不偷 Cookie，不使用代理池，不抓个人信息，不自动下单，不接淘宝、京东、1688、得物默认适配器，不把结果表述为最终采购结论，不编造字段。

## 完成内容

### 1. 文档收口

已更新 `TASKS.md`：

1. 当前阶段改为“阶段10：客户复核回填闭环”。
2. 阶段9/9.1标记为已完成。
3. 清理阶段8旧下一步、创建 `STAGE8_PLAN.md` 等过时表述。
4. 增加阶段10目标、输入输出、验收标准和安全红线。

已新增 `STAGE10_PLAN.md`，记录阶段10计划、输入格式、回填规则、输出字段、`main.py` 接入方式和验收口径。

### 2. 新增复核回填模块

新增 `src/crawler/review_apply.py`，实现：

1. `load_review_filled(path)`
2. `apply_manual_reviews(products_path, review_filled_path, output_products_path, output_report_path)`

支持人工补齐文件两种格式：

1. 顶层数组。
2. 对象中包含 `review_items` 数组。

当没有人工补齐文件时，可生成空的合法 `reviewed_products.json` 和 `review_report.json`，不阻断主流程。

### 3. 回填匹配规则

匹配逻辑：

1. 优先按 `url` 匹配。
2. 复核项 `url` 为空时，按 `title + source` 弱匹配。
3. 匹配不到的复核项进入 `unmatched_review_items`，流程不崩溃。

`review_status` 处理：

1. `approved`：允许进入 `reviewed_products.json`。
2. `rejected`：不进入 `reviewed_products.json`，写入 `rejected_items`。
3. `needs_more_info`：不进入 `reviewed_products.json`，写入 `unresolved_items`。

### 4. 字段覆盖规则

仅覆盖人工明确确认且非空的字段：

1. `confirmed_price` -> `price`
2. `confirmed_dimensions` -> `dimensions`
3. `confirmed_material` -> `material`
4. `confirmed_installation_service` -> `service_text` 或 `installation_service`
5. `confirmed_source` -> `source`
6. `confirmed_evidence_text` -> `evidence_text` 和 `evidence`
7. `confirmed_fields` -> `reviewed_fields`
8. `review_note` -> `review_note`

保守规则：

1. 不因为 `approved` 自动补空字段。
2. 未确认字段保持原值或空值。
3. 回填后仍缺关键字段时，继续 `manual_review_required=true`。
4. 不编造价格、尺寸、材质、安装服务、来源或证据文本。

### 5. 输出文件

`outputs/reviewed_products.json`：

1. 顶层商品数组。
2. 保留原商品字段。
3. 新增 `review_status`、`review_note`、`reviewed_at`、`reviewed_fields`、`manual_review_required`、`remaining_missing_fields`、`review_source`。

`outputs/review_report.json`：

1. `total_review_items`
2. `approved_count`
3. `rejected_count`
4. `needs_more_info_count`
5. `reviewed_products_count`
6. `unresolved_items`
7. `rejected_items`
8. `unmatched_review_items`
9. `field_updates_count`
10. `input_paths`
11. `output_paths`
12. `notice`

`notice` 固定为：

```text
复核结果为人工补充的采购辅助信息，不代表最终采购结论。
```

### 6. main.py 接入

`main.py` 保持旧 `run_pipeline` 调用兼容。

未显式指定商品 JSON 时，商品读取优先级为：

1. `outputs/reviewed_products.json` 有效且含 `approved` 商品则优先。
2. `outputs/crawler_products.json`。
3. `data/sample_products.json`。

返回结果保留旧字段，并可新增：

1. `reviewed_products_path`
2. `review_report_path`

## 测试覆盖

新增 `tests/test_stage10_review_apply.py`，覆盖：

1. `load_review_filled` 支持顶层数组。
2. `load_review_filled` 支持对象 `review_items`。
3. `approved` 按 URL 覆盖确认字段。
4. `rejected` 不进入 `reviewed_products.json`。
5. `needs_more_info` 进入 `unresolved_items`。
6. URL 为空时按 `title + source` 匹配。
7. 匹配不到进入 `unmatched_review_items`。
8. `approved` 但仍缺关键字段时继续复核。
9. 完整复核商品 `manual_review_required=false`。
10. `main.py` 优先读取 `reviewed_products.json`，无效则回退。

阶段5-9.1旧测试继续通过。

## 验收结果

已执行并通过：

```text
python -m unittest discover tests
python -m src.product_fetcher
python -m src.crawler.review
python -m src.crawler.review_apply
python main.py
python -m json.tool outputs/manual_review_items.json
python -m json.tool outputs/reviewed_products.json
python -m json.tool outputs/review_report.json
python -m json.tool outputs/ranked_products.json
python -m json.tool outputs/responses.json
```

补充执行：

```text
AST syntax check OK
```

说明：`python -m compileall main.py src tests` 在当前 Windows 环境中因覆盖已有 `__pycache__` 文件被拒绝访问，属于 `.pyc` 写入权限问题；源码已通过单元测试、入口运行和 AST 语法检查。

## 自查自纠

已确认禁止文件无 diff：

1. `app.py`
2. `src/doc_writer.py`
3. `src/response_builder.py`
4. `src/product_loader.py`
5. `src/product_ranker.py`
6. `config/crawler_config.json`
7. `data/seed_urls.json`
8. `data/sample_products.json`

自查发现并修正一处小问题：

1. 直接运行 `python -m src.crawler.review_apply` 且没有人工补齐文件时，`review_report.json` 曾记录一个不存在的 `outputs/manual_review_filled.json` 路径。
2. 已修正为缺文件时 `review_filled` 记录为空字符串。

## 当前产物状态

当前仓库没有真实人工补齐文件：

1. `data/manual_review_filled.json` 不存在。
2. `outputs/manual_review_filled.json` 不存在。

因此当前 `outputs/reviewed_products.json` 为合法空数组，`outputs/review_report.json` 为零计数报告。这是无人工补齐输入时的预期安全结果。

## 残余风险

1. 尚未使用真实客户人工补齐文件跑业务验收。
2. 阶段10复核元数据已保存在 `reviewed_products.json`，但旧 `product_loader`、`product_ranker`、`response_builder` 不直接消费这些新增元数据；阶段10按要求未修改旧接口。
3. 当前工作树仍有阶段9/9.1既有未提交改动，交付前需要按版本管理策略统一整理。

## 交付判断

阶段10达到当前交付标准：

1. 功能闭环已实现。
2. 安全红线已遵守。
3. 阶段10新增测试通过。
4. 阶段5-9.1旧测试通过。
5. 主流程可运行。
6. JSON 产物格式合法。
7. 禁止文件未被触碰。
8. 不把复核结果称为最终采购结论。

## 下一阶段建议

阶段11建议做“客户复核文件模板与校验器”：

1. 生成可填写的 `manual_review_filled.json` 模板。
2. 校验 `review_status` 枚举值。
3. 校验空 `confirmed_*`、重复复核项、未知字段和匹配冲突。
4. 输出客户可读的校验报告。
5. 在不破坏旧接口的前提下，评估是否让排序和 Word 输出显式展示阶段10复核元数据。
