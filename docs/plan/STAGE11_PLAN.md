# 阶段 11 计划：客户复核文件模板与校验器

## 目标

阶段 11 只补齐客户复核文件的填写模板与填写结果校验能力：

1. 根据 `outputs/manual_review_items.json` 生成 `outputs/manual_review_filled_template.json`。
2. 校验 `data/manual_review_filled.json` 或 `outputs/manual_review_filled.json`。
3. 输出客户可读的 `outputs/manual_review_validation_report.json`。
4. 在阶段10回填前复用校验器，warning 不阻断，error 才阻断。

## 非目标

1. 不改旧接口。
2. 不做 Word 展示增强。
3. 不改推荐算法。
4. 不新增淘宝、京东、1688、得物默认适配器。
5. 不把校验结果或复核结果称为最终采购结论。

## 输入

1. `outputs/manual_review_items.json`
2. `data/manual_review_filled.json`
3. `outputs/manual_review_filled.json`
4. `outputs/crawler_products.json`

## 输出

1. `outputs/manual_review_filled_template.json`
2. `outputs/manual_review_validation_report.json`
3. 阶段10既有输出仍为 `outputs/reviewed_products.json` 和 `outputs/review_report.json`

## 模板字段

每条 `review_items` 模板项包含：

```text
title
url
source
missing_fields
risk_reason
suggested_action
review_status
review_note
confirmed_price
confirmed_dimensions
confirmed_material
confirmed_installation_service
confirmed_source
confirmed_evidence_text
confirmed_fields
```

默认值：

1. `review_status` 为空字符串。
2. `review_note` 为空字符串。
3. `confirmed_*` 为空字符串。
4. `confirmed_fields` 为空数组。

保守规则：

1. 保留原始 `title`、`url`、`source`。
2. 不自动填任何 `confirmed_*` 字段。
3. 不编造字段。

## 校验规则

1. `review_status` 只能是 `approved`、`rejected`、`needs_more_info` 或空。
2. `approved` 无任何 confirmed 信息时 warning。
3. `rejected` 无 `review_note` 时 warning。
4. `needs_more_info` 无 `review_note` 时 warning。
5. `confirmed_fields` 必须是数组，或可解析字符串。
6. 未知字段进入 `unknown_field_items`，不崩溃。
7. 重复复核项按 `url`，或空 URL 时按 `title + source` 识别。
8. 无法匹配候选商品时进入 `unmatched_items`。
9. 空 `review_status` 进入 `incomplete_items`。
10. `confirmed_*` 为空不报错。

## 校验报告字段

```text
total_items
valid_items_count
error_count
warning_count
errors
warnings
duplicate_items
unmatched_items
incomplete_items
unknown_field_items
input_paths
output_paths
notice
```

`notice` 固定包含：

```text
校验结果仅用于辅助人工复核，不代表最终采购结论。
```

## 验收命令

```text
python -m unittest discover tests
python -m src.crawler.review
python -m src.crawler.review_apply
python main.py
python -m json.tool outputs/manual_review_filled_template.json
python -m json.tool outputs/manual_review_validation_report.json
python -m json.tool outputs/reviewed_products.json
python -m json.tool outputs/review_report.json
git status
```

## 下一阶段建议

阶段 12 可选择：

```text
Word 交付报告增强或复核状态展示。
```
