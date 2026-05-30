# 阶段12计划：简单操作界面

## 目标

为阶段1-11已完成能力提供一个本地 Streamlit 操作界面，让用户不用命令行也能查看项目状态、运行公开 URL 采集、运行主推荐流程、生成复核模板、校验客户复核文件、执行复核回填，并查看输出路径和简短结果摘要。

## 范围

本阶段只新增轻量 UI 壳层，不重写业务逻辑，不新增平台适配器，不修改阶段1-11旧接口。

允许新增：

```text
STAGE12_PLAN.md
ui_streamlit.py
tests/test_stage12_ui_smoke.py
```

允许小改：

```text
TASKS.md
requirements.txt
```

## UI入口

```text
streamlit run ui_streamlit.py
```

页面标题：

```text
采购商品推荐与Word自动填充系统
```

## 功能设计

1. 侧边栏展示当前阶段与安全提示。
2. 首页展示固定项目输入、输出路径。
3. 展示关键文件是否存在。
4. 操作按钮调用既有函数：
   - 公开 URL 采集：`src.crawler.pipeline.run_crawler`
   - 主推荐流程：`main.run_pipeline`
   - 复核填写模板：`src.crawler.review_template.generate_review_template`
   - 复核填写校验：`src.crawler.review_validate.validate_review_filled`
   - 空校验报告：`src.crawler.review_validate.write_empty_validation_report`
   - 复核回填：`src.crawler.review_apply.apply_manual_reviews`
   - 空回填输出：`src.crawler.review_apply.write_empty_review_outputs`
5. 每次操作统一展示成功状态、摘要、输出路径和错误信息。

## 固定路径

```text
data/办公屏风01模板样例.docx
data/sample_products.json
data/seed_urls.json
outputs/crawler_products.json
outputs/manual_review_items.json
outputs/manual_review_filled_template.json
outputs/manual_review_validation_report.json
outputs/reviewed_products.json
outputs/review_report.json
outputs/recommendation_result.docx
```

## 不做事项

1. 不做上传功能。
2. 不改采集、复核、推荐、Word 写回业务逻辑。
3. 不接入淘宝、京东、1688、得物默认适配器。
4. 不绕登录、验证码、风控。
5. 不偷 Cookie，不用代理池，不抓个人信息，不自动下单。
6. 不编造字段，不把未确认字段当成已确认。

## 验收

1. `ui_streamlit.py` 可导入。
2. 存在 `main` 或 `render_app` 函数。
3. 导入时不直接执行 Streamlit 主流程。
4. 旧接口不被修改。
5. 阶段5-11旧测试仍通过。
6. 用户提供的阶段12验收命令通过或给出明确失败原因。
