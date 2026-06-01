# 阶段 2：商品数据闭环实施计划

## Summary

基于阶段 1 已完成的 Word 上传、技术参数解析、模拟响应写回和 `output.docx` 下载闭环，阶段 2 只接入本地商品数据。

目标是让系统能读取 `data/products.json`，统一商品字段，并在 Streamlit 页面展示候选商品列表。阶段 2 不做爬虫、不做 AI、不做数据库、不做登录、不做商品评分、不做真实推荐、不写回推荐商品汇总表。

## Key Changes

允许修改或新增：

- 新增 `STAGE2_PLAN.md`：记录本阶段实施计划。
- 新增 `data/products.json`：本地候选商品样例数据。
- 新增 `src/product_loader.py`：读取和规范化商品 JSON。
- 修改 `app.py`：在现有阶段 1 页面中增加“本地候选商品”展示区。
- 如需记录阶段结果，后续可新增 `STAGE2_SUMMARY.md`，但仅在阶段 2 验收后再写。

禁止修改范围：

- 不修改 `PROJECT_CONTROL.md`、`FLOW.md`、`TASKS.md`、`STAGE1_PLAN.md`、`STAGE1_SUMMARY.md`。
- 不修改 `src/doc_parser.py`、`src/doc_writer.py`、`src/mock_response.py` 的阶段 1 既有行为。
- 不新增爬虫、搜索、AI、数据库、登录、评分排序、推荐生成、Word 推荐汇总表。
- 不重构项目结构，不引入新的前端框架，不做复杂页面美化。

## Implementation Changes

`data/products.json` 使用 UTF-8 JSON，顶层为数组，准备 6 到 10 条本地样例商品数据，其中至少 5 条办公屏风相关，至少 1 条明显无关商品用于后续阶段排序验证。每条商品固定字段为：

```json
{
  "platform": "京东/淘宝/本地样例",
  "title": "商品名称",
  "price": 899,
  "shop": "店铺名称",
  "url": "https://example.com/product/1",
  "image_url": "",
  "specs_text": "尺寸、材质、结构等参数文本",
  "service_text": "配送、安装、售后等服务文本",
  "raw_text": "完整商品原始文本或样例说明"
}
```

`src/product_loader.py` 提供最小商品数据读取能力：

- `PRODUCT_FIELDS` 固定字段顺序。
- `load_products(path)` 读取 UTF-8 JSON，要求顶层是数组。
- `normalize_product(item)` 补齐缺失字段，缺失文本字段使用空字符串，缺失价格使用 `None`。
- 不生成 `clean_products.json`，阶段 2 只做内存字段统一，为阶段 3 预留输入。

`app.py` 保留阶段 1 上传和下载闭环，在页面中增加“本地候选商品”展示区：

- 从 `data/products.json` 读取商品。
- 显示商品数量。
- 表格展示 `title`、`platform`、`price`、`shop`、`url`、`specs_text`、`service_text`。
- 页面文案使用“候选商品”或“本地样例商品”，不使用“推荐商品”。
- JSON 缺失、格式错误或字段缺失时显示明确错误信息，不影响阶段 1 Word 闭环继续运行。

## Acceptance Criteria

- `data/products.json` 存在，格式合法，可被 Python JSON 正常读取。
- 商品数据至少 6 条，其中至少 5 条办公屏风相关，至少 1 条无关商品。
- 每条商品都包含 `platform`、`title`、`price`、`shop`、`url`、`image_url`、`specs_text`、`service_text`、`raw_text`。
- Streamlit 页面能展示候选商品名称、平台、价格、链接、参数文本。
- 字段缺失时页面不崩溃，缺失值以空字符串或 `None` 处理。
- 阶段 1 原有功能仍可用：上传样例 Word、展示 13 条参数、生成模拟响应、下载 `output.docx`。
- 页面不出现评分、排序、匹配理由、风险提示、Top 商品、真实推荐、AI、爬虫、数据库或登录相关功能。

## Test Plan

- 运行 `python -m json.tool data/products.json`，确认 JSON 格式合法。
- 运行商品读取函数，确认能读出商品数量并补齐字段。
- 启动 `python -m streamlit run app.py`，确认页面显示候选商品表格。
- 上传 `data/办公屏风01模板样例.docx`，确认阶段 1 Word 闭环不受影响。
- 临时验证缺失字段商品不会导致页面崩溃，正式数据仍保持字段完整。

## Risks And Defaults

- 本地商品数据可能被误解为真实推荐；页面必须标注为“候选商品”或“本地样例商品”。
- 商品字段过少会影响阶段 3 评分；阶段 2 的样例数据应在 `specs_text` 中保留尺寸、材质、服务等关键文本。
- 中文 JSON 需要统一使用 UTF-8。
- 阶段 2 不输出 `ranked_products.json`、`responses.json` 或新的 Word 推荐汇总表。
