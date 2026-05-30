# 阶段10计划：客户复核回填闭环

## 目标

读取客户或人工补齐后的复核文件，将明确批准且可匹配到原候选商品的条目回填为 `outputs/reviewed_products.json`，同时生成 `outputs/review_report.json`。已复核商品可按优先级重新进入推荐排序与 Word 写回流程。

## 输入

1. `outputs/crawler_products.json`：阶段8/9生成的候选商品。
2. `outputs/manual_review_items.json`：阶段9/9.1生成的人工复核清单。
3. `data/manual_review_filled.json` 或 `outputs/manual_review_filled.json`：人工补齐后的复核结果，可不存在。

人工补齐文件支持顶层数组，或对象中包含 `review_items` 数组。每条记录可包含：

```text
title, url, source, review_status, review_note,
confirmed_price, confirmed_dimensions, confirmed_material,
confirmed_installation_service, confirmed_source,
confirmed_evidence_text, confirmed_fields
```

## 回填规则

1. `review_status=approved` 的匹配商品进入 `reviewed_products.json`。
2. `review_status=rejected` 不进入已复核商品，写入 `rejected_items`。
3. `review_status=needs_more_info` 不进入已复核商品，写入 `unresolved_items`。
4. 匹配优先按 `url`；当复核项 `url` 为空时，按 `title + source` 弱匹配。
5. 匹配不到的复核项写入 `unmatched_review_items`，流程不崩溃。
6. 仅 `confirmed_*` 中有明确值的字段允许覆盖原商品字段。
7. 不因 `approved` 自动补空字段，不编造未确认字段。
8. 回填后仍缺价格、尺寸、材质、安装服务、来源或证据文本时，继续保留 `manual_review_required=true`。

## 输出

`outputs/reviewed_products.json` 为顶层商品数组。每个商品保留原字段，并新增：

```text
review_status, review_note, reviewed_at, reviewed_fields,
manual_review_required, remaining_missing_fields, review_source
```

`outputs/review_report.json` 包含：

```text
total_review_items
approved_count
rejected_count
needs_more_info_count
reviewed_products_count
unresolved_items
rejected_items
unmatched_review_items
field_updates_count
input_paths
output_paths
notice
```

`notice` 固定声明：复核结果为人工补充的采购辅助信息，不代表最终采购结论。

## main.py接入

保持 `run_pipeline` 旧调用兼容。未显式指定商品 JSON 时，商品读取优先级为：

1. `outputs/reviewed_products.json` 有效则优先。
2. `outputs/crawler_products.json`。
3. `data/sample_products.json`。

返回结果可新增 `reviewed_products_path` 和 `review_report_path`，不删除旧返回字段。

## 验收标准

1. `load_review_filled` 支持顶层数组和对象 `review_items`。
2. `approved` 可按 URL 或 `title + source` 匹配并只覆盖确认字段。
3. `rejected` 和 `needs_more_info` 不进入 `reviewed_products.json`。
4. 未匹配复核项进入 `unmatched_review_items`，不中断流程。
5. 已批准但仍缺关键字段的商品继续标记 `manual_review_required=true`。
6. 完整复核商品可清除 `manual_review_required`。
7. 阶段5-9.1既有测试继续通过。
8. 阶段10新增测试通过。

## 安全红线

1. 不绕登录、验证码或平台风控。
2. 不偷 Cookie。
3. 不使用代理池规避限制。
4. 不抓取个人信息。
5. 不自动下单。
6. 不接淘宝、京东、1688、得物默认适配器。
7. 不把结果称为最终采购结论。
8. 不得编造字段或把未确认字段当作已确认。
