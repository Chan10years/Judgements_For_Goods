# 阶段 1：Word 闭环完成说明

## 1. 创建或修改的文件

本阶段创建了以下文件：

- `requirements.txt`
  - 声明最小依赖：`streamlit`、`python-docx`。
- `app.py`
  - Streamlit 页面入口。
  - 支持上传 `.docx`、展示解析结果、生成模拟响应、写回 Word、下载输出 Word。
- `src/__init__.py`
  - 标记 `src` 为 Python 模块目录。
- `src/doc_parser.py`
  - 负责解析 Word 中的技术参数表。
  - 提取字段：`index`、`name`、`unit`、`required_value`、`response_value`。
- `src/mock_response.py`
  - 负责为每条技术参数生成固定模拟响应。
- `src/doc_writer.py`
  - 负责将模拟响应写回“投标人响应值”列。
- `STAGE1_SUMMARY.md`
  - 当前阶段完成说明。

本阶段生成了以下运行产物：

- `outputs/input.docx`
- `outputs/requirements.json`
- `outputs/output.docx`

未修改以下禁止文件：

- `PROJECT_CONTROL.md`
- `FLOW.md`
- `TASKS.md`
- `STAGE1_PLAN.md`

## 2. 如何运行

先安装依赖：

```powershell
python -m pip install -r requirements.txt
```

启动页面：

```powershell
python -m streamlit run app.py
```

打开页面后上传：

```text
data/办公屏风01模板样例.docx
```

页面会展示解析出的技术参数，并提供生成和下载 `output.docx` 的按钮。

## 3. 如何验收

验收步骤：

1. 打开 Streamlit 页面。
2. 上传 `data/办公屏风01模板样例.docx`。
3. 确认页面展示 13 条技术参数。
4. 点击“生成模拟响应并导出 Word”。
5. 下载 `output.docx`。
6. 打开输出 Word，确认“投标人响应值”列已填充。

已完成的本地验证：

- 解析结果数量：13 条。
- 输出 Word 中技术参数数量：13 条。
- 输出 Word 中非空响应数量：13 条。
- `outputs/output.docx` 已生成并可被程序重新读取。

## 4. 阶段 1 是否达标

阶段 1 已达标。

已完成：

- Streamlit 页面支持上传 `.docx`。
- 可解析样例 Word 中的技术参数表。
- 页面可展示解析结果。
- 每条参数可生成模拟响应。
- 模拟响应可写回“投标人响应值”列。
- 可生成 `outputs/output.docx`。
- 页面提供下载按钮。

未进入以下禁止范围：

- 淘宝爬虫。
- 京东爬虫。
- AI。
- 商品数据。
- 商品评分。
- 推荐汇总表。
- 数据库。
- 登录系统。
- 复杂前端。

## 5. 遗留风险

- 当前只适配样例 Word 的固定表头结构，不做通用模板识别。
- 如果样例 Word 正在被 Word 或 WPS 打开，可能导致读取或写出失败。
- `python-docx` 写入单元格可能轻微影响单元格内部局部格式，但不会重建整张表。
- 当前响应是模拟内容，不代表真实商品参数匹配结果。
