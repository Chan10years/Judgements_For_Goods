# 阶段 11 总结：客户复核文件模板与校验器

## 1. 阶段目标

阶段 11 已完成客户复核文件模板与填写结果校验能力，范围严格限定在复核模板、校验报告和阶段10回填前的格式校验，不进入 Word 展示增强，不修改推荐算法，不改旧接口。

完成目标：

1. 根据 `outputs/manual_review_items.json` 生成客户可填写模板 `outputs/manual_review_filled_template.json`。
2. 校验 `data/manual_review_filled.json` 或 `outputs/manual_review_filled.json`。
3. 输出客户可读的 `outputs/manual_review_validation_report.json`。
4. 在 `apply_manual_reviews` 前复用校验器：warning 不阻断，error 才阻断。

## 2. 模板字段

模板顶层结构：

```json
{
  "review_items": []
}
```

每条模板项包含：

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

默认值规则：

1. `review_status` 为空字符串。
2. `review_note` 为空字符串。
3. `confirmed_price`、`confirmed_dimensions`、`confirmed_material`、`confirmed_installation_service`、`confirmed_source`、`confirmed_evidence_text` 为空字符串。
4. `confirmed_fields` 为空数组。
5. 保留原始 `title`、`url`、`source`，便于阶段10按原始信息匹配。
6. 不自动填任何 `confirmed_*` 字段，不把未确认字段当成已确认。

## 3. 校验规则

已实现的校验规则：

1. `review_status` 只能是 `approved`、`rejected`、`needs_more_info` 或空。
2. `approved` 无任何 `confirmed_*` 非空字段且 `confirmed_fields` 为空时，写入 warning。
3. `rejected` 无 `review_note` 时，写入 warning。
4. `needs_more_info` 无 `review_note` 时，写入 warning。
5. `confirmed_fields` 必须是数组，或可解析为字段列表的字符串；严重格式错误写入 error。
6. 未知字段写入 `unknown_field_items` 和 warning，不崩溃。
7. 重复复核项按 `url` 识别；`url` 为空时按 `title + source` 识别，并写入 `duplicate_items`。
8. 复核项无法匹配 `outputs/crawler_products.json` 时写入 `unmatched_items`。
9. `review_status` 为空时写入 `incomplete_items`。
10. `confirmed_*` 为空不报错，仅按场景给 warning。

校验报告固定包含提示：

```text
校验结果仅用于辅助人工复核，不代表最终采购结论。
```

## 4. 验收命令

阶段 11 已执行并通过：

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

补充自查：

```text
只读 AST 语法检查通过。
```

说明：额外尝试的 `python -m compileall src tests` 因现有 `__pycache__` 写权限报 `PermissionError`，不属于阶段11验收命令，且单测和只读语法检查已证明代码可导入运行。

## 5. 测试结果

测试结果：

```text
python -m unittest discover tests
Ran 46 tests
OK
```

阶段 11 新增测试覆盖：

1. 根据 `manual_review_items.json` 生成模板。
2. 模板包含所有必需字段。
3. `approved` 且无 confirmed 字段产生 warning。
4. 非法 `review_status` 产生 error。
5. `rejected` 无 `review_note` 产生 warning。
6. `needs_more_info` 无 `review_note` 产生 warning。
7. 重复 URL 被识别。
8. URL 为空时 `title + source` 重复被识别。
9. 未知字段进入 `unknown_field_items`。
10. 无法匹配商品进入 `unmatched_items`。
11. 空 `review_status` 进入 `incomplete_items`。
12. 阶段5-10旧测试仍通过。

## 6. 触碰范围

阶段 11 触碰范围符合要求：

1. 新增 `src/crawler/review_template.py`。
2. 新增 `src/crawler/review_validate.py`。
3. 新增 `tests/test_stage11_review_template_validate.py`。
4. 小改 `src/crawler/review_apply.py`。
5. 更新 `TASKS.md`。
6. 新增 `STAGE11_PLAN.md`。

未触碰禁止文件：

1. 未修改 `app.py`。
2. 未修改 `src/doc_writer.py` 旧接口。
3. 未修改 `src/response_builder.py` 旧接口。
4. 未修改 `src/product_loader.py` 旧接口。
5. 未修改 `src/product_ranker.py` 旧接口。
6. 未修改阶段1-10归档总结文件。
7. 未修改 `config/crawler_config.json`。
8. 未修改 `data/seed_urls.json`。
9. 未修改 `data/sample_products.json`。

## 7. 残余风险

1. 当前默认没有客户填写文件时，校验报告会产生一条 warning：未发现客户填写后的人工复核文件。这是预期提示，不影响运行。
2. 工作区仍存在阶段9/10上下文遗留改动和未跟踪文件，交付前需要统一确认归属并提交，避免阶段边界混淆。
3. `__pycache__` 写权限会影响 `compileall` 这类缓存写入检查；当前验收命令不依赖该检查。

## 8. 后续路线

总体路线：

```text
阶段 12：简单操作界面
阶段 13：真实样例数据验收
阶段 14：错误处理和可维护性
阶段 15：交付包整理
阶段 16：最终验收文档
```
