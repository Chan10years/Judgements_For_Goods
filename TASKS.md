采购商品推荐与 Word 自动填充系统任务清单

## 1. 当前项目状态

项目文件夹：

```text
D:\CodeLibrary\Judgements_For_Goods
```

当前阶段：

```text
阶段12.5：Word交付报告增强
```

当前最高优先级：

```text
阶段12.5 Word交付报告增强已完成，准备进入阶段13真实样例数据验收。
```

## 2. 阶段完成状态

```text
阶段 1-4：已完成
阶段 5-7：已完成
阶段 8：公开 URL 采集底座 v1 已完成
阶段 8.1：采集生产硬化已完成
阶段 9：客户指定数据源适配与人工复核闭环 v1 已完成
阶段 9.1：客户交付审计与风险复核已完成
阶段 10：客户复核回填闭环已完成
阶段 11：客户复核文件模板与校验器已完成
阶段12：简单操作界面已完成
阶段12.5：Word交付报告增强已完成
阶段13：真实样例数据验收待开始
```

## 3. 已完成能力摘要

### 阶段 1-4：Word 读取、推荐响应与写回

状态：已完成。

完成能力：

1. 读取采购技术规范 Word。
2. 解析技术参数表。
3. 生成参数响应和风险提示。
4. 选择 Top 3 候选商品。
5. 将推荐结果写回 Word，并输出可打开的交付文档。

### 阶段 5-7：商品标准化、规则排序、主流程

状态：已完成。

完成能力：

1. 商品字段标准化增强。
2. 规则评分排序增强。
3. `main.py` 端到端流程完成。
4. 保留本地样例商品兜底路径。

### 阶段 8/8.1：公开采集底座与生产硬化

状态：已完成。

完成能力：

1. 保守采集配置、seed URL 校验、robots 检查、限速请求、解析、去重、报告和日志。
2. 默认不预置复杂平台 URL。
3. 外部采集失败或产物无效时，主流程可回退到本地样例商品。

### 阶段 9/9.1：客户数据源适配与交付审计

状态：已完成。

完成能力：

1. 客户手动 JSON 适配器。
2. 客户手动 CSV 适配器。
3. 复用阶段8公开 URL 采集能力的静态页面适配器。
4. `outputs/manual_review_items.json` 人工复核清单。
5. `crawler_report.json` 客户可读 `summary`。
6. `main.py` 可选返回 `manual_review_path`，不影响旧主流程。
7. 客户交付审计已补充风险提示、测试和安全口径。

### 阶段 10：客户复核回填闭环

状态：已完成。

完成能力：

1. 读取 `data/manual_review_filled.json` 或 `outputs/manual_review_filled.json`。
2. 按 `url` 或空链接时按 `title + source` 匹配候选商品。
3. 只回填人工明确填写且非空的 `confirmed_*` 字段。
4. 输出 `outputs/reviewed_products.json` 和 `outputs/review_report.json`。
5. 让已复核且 approved 的商品优先进入推荐与 Word 写回流程。

### 阶段 11：客户复核文件模板与校验器

状态：已完成。

完成能力：

1. 根据 `outputs/manual_review_items.json` 生成 `outputs/manual_review_filled_template.json`。
2. 模板保留原始 `title`、`url`、`source`，并提供 `review_status`、`review_note`、`confirmed_*`、`confirmed_fields` 供客户填写。
3. 校验 `data/manual_review_filled.json` 或 `outputs/manual_review_filled.json`。
4. 输出 `outputs/manual_review_validation_report.json`，包含错误、警告、重复项、未匹配项、未完成项、未知字段项。
5. 在阶段10回填前复用校验器：warning 不阻断，严重格式 error 才阻断。

### 阶段 12：简单操作界面

状态：已完成。

完成能力：

1. 新增本地 Streamlit 操作入口 `ui_streamlit.py`。
2. 展示项目主要输入、输出路径和关键文件存在状态。
3. 可触发公开 URL 采集、主推荐流程、复核模板生成、复核填写校验和复核回填。
4. 每次操作后展示成功状态、简短摘要、输出路径和错误信息。
5. 保持阶段1-11业务逻辑和旧接口不变。

### 阶段 12.5：Word交付报告增强

状态：已完成。

目标能力：

1. 在 `outputs/recommendation_result.docx` 中增加客户可读交付报告摘要。
2. 说明商品数据来源优先级和当前实际使用的数据源。
3. 展示需求数量、候选商品数量、Top候选数量和关键输出路径。
4. 展示人工复核状态、复核计数、未匹配复核项和仍需人工复核的风险提示。
5. 明确价格、尺寸、材质、安装服务、来源、证据文本等字段风险。
6. 列出关键输出文件索引。

## 4. 当前阶段：阶段 12.5

阶段 12.5 名称：

```text
Word交付报告增强
```

阶段 12.5 目标：

1. 增强 Word 输出报告的客户交付说明。
2. 保留 `write_responses` 旧接口和既有返回行为。
3. `main.py` 只传递交付报告元数据，不重写主流程。
4. 不新增采集平台适配器，不改推荐算法。
5. 不把任何结果称为最终采购结论。

## 5. 阶段 12.5 输入

阶段 12.5 复用既有输入：

1. 默认 Word 文档。
2. 当前实际使用的候选商品 JSON。
3. `outputs/reviewed_products.json`。
4. `outputs/review_report.json`。
5. 既有阶段1-12输出文件。

## 6. 阶段 12.5 输出

阶段 12.5 输出：

1. 增强后的 `outputs/recommendation_result.docx`。
2. `STAGE12_5_PLAN.md`。
3. `STAGE12_5_SUMMARY.md`。
4. `tests/test_stage12_5_word_delivery_report.py`。

## 7. 阶段 12.5 约束

1. 只做 Word 交付说明增强，不进入阶段13真实样例数据验收。
2. 不改阶段1-12旧接口。
3. 不新增采集平台，不新增上传功能。
4. 不绕登录、验证码或风控。
5. 不自动下单，不抓个人信息。
6. 不把输出称为最终采购结论。

## 8. 阶段 12.5 验收方向

1. `write_responses` 旧接口仍可调用。
2. 不传新增参数时旧 Word 输出仍能生成。
3. 传入交付报告元数据时，Word 中出现交付报告摘要、数据来源说明、人工复核状态说明和字段风险提示。
4. 阶段5-12现有测试仍通过。
4. `main.py` 端到端流程仍通过。
5. 不出现把推荐结果称为最终采购结论的违规表述。

## 9. 总体路线

```text
阶段12：简单操作界面（已完成）
阶段12.5：Word交付报告增强
阶段13：真实样例数据验收
阶段 14：错误处理和可维护性
阶段 15：交付包整理
阶段 16：最终验收文档
```

## 10. 当前安全红线

1. 不绕登录、验证码或风控。
2. 不偷 Cookie。
3. 不用代理池。
4. 不抓个人信息。
5. 不自动下单。
6. 不接淘宝、京东、1688、得物默认适配器。
7. 不把采集结果、复核结果、校验结果或推荐结果称为最终采购结论。
8. 不得编造字段。
9. 不得自动把未确认字段当成已确认。
10. 不删除旧接口。
11. 不破坏 `main.py` 既有端到端流程。

## 11. Codex 使用规则

每次让 Codex 工作前，必须明确：

1. 当前阶段。
2. 当前任务。
3. 允许修改的文件。
4. 禁止修改的文件。
5. 输入是什么。
6. 输出是什么。
7. 失败兜底是什么。
8. 验收标准是什么。
9. 安全红线是什么。

## 12. 文档维护规则

阶段 12.5 允许新增或修改范围：

```text
允许新增：STAGE12_5_PLAN.md、STAGE12_5_SUMMARY.md、tests/test_stage12_5_word_delivery_report.py
允许小改：TASKS.md、main.py、src/doc_writer.py
```

阶段 12 归档文件：

```text
TASKS.md
STAGE12_PLAN.md
```

阶段 12.5 禁止顺手修改：

1. `app.py`
2. `src/product_loader.py` 旧接口
3. `src/response_builder.py` 旧接口
4. `src/product_ranker.py` 旧接口
5. `src/crawler` 核心采集逻辑
6. 阶段 1-12 归档总结文件
7. `config/crawler_config.json`
8. `data/seed_urls.json`
9. `data/sample_products.json`

## 13. 下一阶段建议

阶段 13 可做：

```text
阶段13：真实样例数据验收。
```
