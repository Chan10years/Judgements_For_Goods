# 阶段 9.1 审查总结：客户交付审计与风险复核

## 1. 审查结论

阶段 9.1 对阶段 9 的客户交付强度进行了复核，并完成小范围修复与补测。阶段 9 可作为客户交付候选归档；下一阶段可以进入阶段 10“客户复核回填闭环”。

本审查未新增大功能，未进入阶段 10，未重构主流程，未修改旧接口。

## 2. 审查范围

已审查：

1. `STAGE9_PLAN.md`
2. `TASKS.md`
3. `main.py`
4. `src/crawler/pipeline.py`
5. `src/crawler/review.py`
6. `src/crawler/adapters/base.py`
7. `src/crawler/adapters/manual_json_adapter.py`
8. `src/crawler/adapters/manual_csv_adapter.py`
9. `src/crawler/adapters/static_page_adapter.py`
10. `tests/test_stage9_adapters.py`
11. `tests/test_stage8_crawler.py`
12. `.gitignore`

## 3. 已修复问题

1. `crawler_report.summary` 补充“跳过 URL 数”，客户阅读口径更完整。
2. JSON/CSV 字段映射补充 `店铺`、`供应商`、`URL`、`商品图片` 等常见客户字段。
3. CSV/JSON 未识别字段保留到 `extra`，不影响旧主流程。
4. 人工复核 `suggested_action` 按缺失字段生成更具体的人工动作。
5. `.gitignore` 补充缓存、`.env`、JSON/DOCX 运行产物、stage8 测试工作区等忽略规则。
6. `TASKS.md` 收口为阶段 9 已完成、阶段 9.1 审查清理、下一阶段建议阶段 10。

## 4. 适配器审查结果

`ProductSourceAdapter` 定义了统一 `load_candidates()` 接口，并输出可进入 `normalize_products`、`rank_products` 与 Word 写回流程的商品候选结构。

手动 JSON、手动 CSV 和静态公开页面适配器均遵守“不编造字段”的原则。缺价格、尺寸、材质、安装服务、来源或证据时，商品会进入人工复核。

静态公开页面适配器复用阶段 8 `run_crawler`，继续遵守 robots、限速、超时和报告机制，不绕登录、验证码或平台风控。

## 5. 人工复核规则审查结果

人工复核项包含：

1. `title`
2. `url`
3. `source`
4. `missing_fields`
5. `manual_review_required`
6. `evidence_text`
7. `risk_reason`
8. `suggested_action`

必须复核的情况已覆盖：缺价格、缺尺寸、缺材质、缺安装服务、缺明确来源、缺 `evidence_text`、`parse_success` 为 false、上游 `manual_review_required` 为 true。

字段完整且证据充足的商品不会无理由进入复核。

## 6. 报告与主流程审查结果

`crawler_report.summary` 包含客户可读字段：本次采集 URL 数、成功商品数、失败 URL 数、跳过 URL 数、需人工复核商品数、主要失败原因、输出文件路径和免责声明。

`main.py` 保持旧调用方式和旧返回字段不变，仅在 `manual_review_items.json` 存在时增加 `manual_review_path`。

## 7. 验收命令

阶段 9.1 已执行：

```bash
python -m unittest discover tests  # Ran 25 tests, OK
python -m src.product_fetcher  # 通过，默认 seed 为 0，报告正常生成
python main.py  # 通过，回退本地样例商品并输出 Word
python -m json.tool outputs/crawler_report.json  # 通过
python -m json.tool outputs/manual_review_items.json  # 通过
python -m json.tool outputs/ranked_products.json  # 通过
python -m json.tool outputs/responses.json  # 通过
git status  # 仅显示允许范围内的源码/文档变更；运行产物、缓存、日志未进入待提交列表
```

## 8. 残余风险

1. 客户自定义 JSON/CSV 表头可能继续扩展，后续需按客户样表补充映射。
2. 静态页面采集仍依赖公开页面 HTML，复杂动态页面可能只能进入失败报告或人工复核。
3. 本系统输出仍是采购辅助候选，不能替代最终采购结论、合同审核或人工验收。

## 9. 下一阶段建议

阶段 10 建议建设客户复核回填闭环：读取人工补齐后的复核结果，形成可审计的修订版候选商品，并在 Word 输出中展示“已复核/待复核”状态。
