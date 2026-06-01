# 阶段 1：Word 闭环实施计划

## 结论

三份文档整体一致：当前只做“Word 能读、能写、能导出”。  
需要注意：`PROJECT_CONTROL.md` 和 `FLOW.md` 里提到的 `products.json`、评分、推荐商品汇总表属于完整 MVP 或后续阶段；阶段 1 以 `TASKS.md` 为准，不进入商品、评分、AI、爬虫。

## 阶段 1 目标

实现最小闭环：

上传 `data/办公屏风01模板样例.docx`  
↓  
解析技术参数表  
↓  
页面展示解析结果  
↓  
生成模拟投标人响应值  
↓  
写回 Word  
↓  
下载 `output.docx`

## 需要创建的文件

- `requirements.txt`  
  声明最小依赖：`streamlit`、`python-docx`。

- `app.py`  
  页面入口。负责上传 Word、展示解析结果、生成模拟响应、调用写回、提供下载按钮。

- `src/__init__.py`  
  标记 `src` 为 Python 模块目录。

- `src/doc_parser.py`  
  解析 Word 表格。查找包含表头 `序号 / 技术参数名称 / 单位 / 项目需求值或表述 / 投标人响应值` 的表格，输出参数列表。

- `src/doc_writer.py`  
  写回 Word。定位同一张技术参数表，把模拟响应写入“投标人响应值”列，保存为新文档。

现有目录与文件继续使用：

- `data/办公屏风01模板样例.docx`
- `outputs/`

## 最小实现方式

1. `app.py` 接收上传的 `.docx`，保存为 `outputs/input.docx`。
2. `doc_parser.py` 解析技术参数表，生成结构：
   `index、name、unit、required_value、response_value`。
3. `app.py` 页面展示解析出的表格。
4. `app.py` 为每一行生成固定模拟响应，例如：  
   `模拟响应：该项参数已识别，当前阶段仅验证 Word 写回，需后续商品数据匹配后复核。`
5. `doc_writer.py` 将响应写入“投标人响应值”列。
6. 输出 `outputs/output.docx`。
7. 页面提供下载按钮。

## 最小运行方式

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

浏览器打开 Streamlit 页面后，上传：

```text
data/办公屏风01模板样例.docx
```

然后下载生成的 `output.docx`。

## 验收标准

- 页面可以上传 `.docx`。
- 能解析出样例 Word 中的 13 条技术参数。
- 页面能展示参数名称、单位、项目需求值、投标人响应值。
- 每条参数都生成非空模拟响应。
- 能生成 `outputs/output.docx`。
- 输出 Word 可以正常打开。
- 原技术参数表仍在。
- “投标人响应值”列全部被填充。
- 不出现商品数据、商品评分、推荐汇总表、淘宝、京东、AI、数据库、登录系统。

## 风险点

- 样例 Word 如果正在被 Word/WPS 打开，可能导致读取或写出失败；运行前关闭文档。
- 阶段 1 只适配当前样例表头，不做通用 Word 模板识别。
- `python-docx` 写入单元格可能轻微影响单元格内局部格式，但不得破坏表格结构。
- 模拟响应不能写成真实承诺，避免被误认为已完成商品匹配。
