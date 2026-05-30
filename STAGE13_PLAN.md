# 阶段13：真实样例数据验收计划

## 1. 阶段边界

阶段13只做真实或半真实样例数据验收，目标是用少量样例跑一遍现有采集、复核、推荐、Word 输出和 UI 触发链路，记录真实数据暴露的问题。

本阶段不开发新功能，不重写业务逻辑，不新增平台适配器，不新增上传功能，不修改推荐算法，不进入阶段14错误处理和可维护性。

## 2. 允许修改范围

允许新增或更新：

```text
STAGE13_PLAN.md
STAGE13_SUMMARY.md
tests/test_stage13_real_sample_acceptance.py
data/stage13_sample_products.json
data/stage13_seed_urls.json
outputs/stage13_acceptance_report.json
TASKS.md
```

禁止修改：

```text
app.py
config/crawler_config.json
data/seed_urls.json
data/sample_products.json
main.py
src/doc_writer.py
src/product_loader.py
src/product_ranker.py
src/response_builder.py
src/crawler/*
ui_streamlit.py
阶段1到阶段12.5归档总结文件
```

## 3. 样例输入

阶段13使用两类输入：

1. `data/stage13_seed_urls.json`：公开可访问、无登录、无验证码、无个人信息的 URL 样例，用于验证采集报告能记录成功、失败、字段缺失和人工复核项。
2. `data/stage13_sample_products.json`：半真实商品 JSON，用于稳定覆盖完整商品、字段缺失商品、证据不足商品、来源不足商品和明显无关商品。

半真实样例只用于链路验收，不代表真实报价、库存、安装服务或最终采购结论。

## 4. 验收流程

1. 校验阶段13样例 JSON 格式。
2. 使用阶段13 URL 文件运行公开 URL 采集流程，并记录成功、失败、跳过和人工复核项。
3. 使用阶段13半真实商品 JSON 生成候选商品，识别字段缺失和证据不足。
4. 生成人工复核清单。
5. 生成客户复核填写模板。
6. 使用一份故意错误的复核填写文件验证校验器能发现问题。
7. 使用一份有效复核填写文件执行复核回填。
8. 使用已复核商品运行主推荐流程并生成 Word。
9. 检查 Word 中是否仍有交付报告摘要、数据来源说明、人工复核状态说明、字段风险提示和输出文件索引。
10. 使用半自动方式验证 Streamlit UI 按钮能触发现有 action 函数。
11. 生成 `outputs/stage13_acceptance_report.json` 和 `STAGE13_SUMMARY.md`。

## 5. 必须执行命令

```text
python -m unittest discover tests
python -m py_compile main.py
python -m py_compile src/doc_writer.py
python -m py_compile ui_streamlit.py
python -m src.product_fetcher
python -m src.crawler.review
python -m src.crawler.review_apply
python main.py
python -m json.tool outputs/ranked_products.json
python -m json.tool outputs/responses.json
git status
```

阶段13还会额外执行：

```text
python -m json.tool data/stage13_seed_urls.json
python -m json.tool data/stage13_sample_products.json
python -m json.tool outputs/stage13_acceptance_report.json
```

## 6. 验收判定

最终结论只能从以下三种选择：

```text
可以进入阶段14
需要补充真实样例后再验收
存在阻断问题，暂不进入阶段14
```

如果完整链路、Word 输出、UI 半自动触发和旧测试均通过，且未触碰禁止文件，则阶段13可通过。

如果半真实链路通过但公开 URL 因网络或页面结构不稳定全部失败，则记录为需要补充真实样例后再验收。

如果主流程、Word 输出、复核回填或禁止文件边界出现阻断，则记录为存在阻断问题，暂不进入阶段14。
