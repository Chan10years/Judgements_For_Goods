# 阶段13.2B执行计划：应急交付 MVP

## 目标

把当前系统从固定路径运行升级为客户可操作的 V1 半自动采购推荐闭环：

1. 客户上传采购 Word。
2. 客户上传候选商品 JSON 或 CSV。
3. 系统解析采购指标。
4. 系统读取并标准化候选商品。
5. 系统执行规则排序并生成 Top 推荐。
6. 系统输出可下载的 Word 推荐报告。
7. 系统提供淘宝/京东搜索关键词和搜索入口辅助。

## 范围边界

本阶段只做 V1 应急交付 MVP，不做淘宝/京东全自动抓取，不绕登录、验证码或风控，不偷 Cookie，不使用代理池，不自动下单，不抓个人信息，不承诺最终采购结论。

淘宝/京东搜索结果抓取、商品详情自动解析、图片证据处理和自动候选池生成属于后续 V2，需要平台授权接口、合规第三方商品搜索 API、客户导出的商品数据或明确授权的公开数据源。

## 允许改动

新增：

1. `STAGE13_2B_PLAN.md`
2. `STAGE13_2B_SUMMARY.md`
3. `tests/test_stage13_2b_delivery_mvp.py`
4. `data/stage13_2b_candidate_products_demo.json`
5. `data/stage13_2b_candidate_products_demo.csv`

小改：

1. `TASKS.md`
2. `ui_streamlit.py`
3. `main.py`
4. `src/doc_writer.py`

## 实施步骤

1. 在 `main.py` 增加 13.2B 候选商品导入函数，复用 `ManualJsonAdapter` 和 `ManualCsvAdapter`。
2. 增加淘宝/京东搜索关键词和搜索链接生成函数，只生成入口，不访问平台页面。
3. 扩展 `run_pipeline`，支持传入已标准化候选商品，同时保留固定路径默认运行能力。
4. 在 `ui_streamlit.py` 增加“应急交付 MVP”区块，支持 Word 与候选文件上传、生成结果展示和 Word 下载。
5. 在 `src/doc_writer.py` 扩展 Top 推荐表，写入尺寸、材质、安装服务、商品链接、图片链接、匹配说明、待复核字段和风险提示。
6. 增加演示 JSON/CSV 与回归测试。
7. 运行验收命令并输出总结。

## 验收口径

1. 固定路径 `python main.py` 仍可运行。
2. `ui_streamlit.py` 可导入，原阶段12按钮仍存在。
3. 上传采购 Word 和候选商品 JSON/CSV 后可生成推荐 Word。
4. 缺失商品字段不会被编造，Word 中写为“待人工复核”或风险提示。
5. 页面提供淘宝/京东搜索关键词和链接，但不自动抓取淘宝/京东页面。
