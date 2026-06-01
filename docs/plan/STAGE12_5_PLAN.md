# 阶段12.5计划：Word交付报告增强

## 目标

在阶段12简单操作界面完成后、阶段13真实样例数据验收前，增强 `outputs/recommendation_result.docx` 的客户交付说明能力，让客户打开 Word 后能理解本次推荐的数据来源、候选输出、人工复核状态、字段风险和关键输出文件。

## 范围

本阶段只增强 Word 输出报告的可读性和交付说明，不进入阶段13真实样例数据验收。

允许新增：

```text
STAGE12_5_PLAN.md
STAGE12_5_SUMMARY.md
tests/test_stage12_5_word_delivery_report.py
```

允许小改：

```text
TASKS.md
main.py
src/doc_writer.py
```

## 实现设计

1. `src/doc_writer.py`
   - 保留 `write_responses(input_docx_path, responses, output_docx_path, summary_products=None)` 旧调用方式。
   - 新增可选参数 `delivery_metadata=None`。
   - 仅在传入 `delivery_metadata` 时追加交付报告说明。

2. `main.py`
   - 不改主流程，不改推荐算法。
   - 只根据现有流程产物生成交付报告元数据。
   - 将元数据传给 `write_responses`。

3. Word 增强内容
   - 交付报告摘要。
   - 数据来源说明。
   - 推荐结果摘要。
   - 人工复核状态说明。
   - 字段风险提示。
   - 输出文件索引。

## 不做事项

1. 不新增采集平台。
2. 不新增上传功能。
3. 不重写推荐算法。
4. 不修改 `app.py`。
5. 不修改 `src/product_loader.py`、`src/product_ranker.py`、`src/response_builder.py` 旧接口。
6. 不修改 `src/crawler` 核心采集逻辑。
7. 不修改 `config/crawler_config.json`、`data/seed_urls.json`、`data/sample_products.json`。
8. 不修改阶段1到12归档总结文件。

## 验收

```text
python -m unittest discover tests
python main.py
python -m py_compile main.py
python -m py_compile src/doc_writer.py
python -m json.tool outputs/ranked_products.json
python -m json.tool outputs/responses.json
git status
```

补充检查：

1. `outputs/recommendation_result.docx` 成功生成。
2. Word 中出现交付报告摘要、数据来源说明、人工复核状态说明和字段风险提示。
3. 不把推荐结果称为最终采购结论。
