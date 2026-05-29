# 阶段 4 计划：候选商品 Top 3 汇总与参数响应写回 Word

## 1. 阶段目标

阶段 4 只做“规则排序结果写回 Word”：基于当前页面解析出的 `requirements` 和当前页面刚生成的 `ranked_products`，生成规则响应中间产物 `outputs/responses.json`，并导出新的 `outputs/output.docx`。

`outputs/responses.json` 基于本地 `outputs/requirements.json` 和 `outputs/ranked_products.json` 生成。它不是 AI 生成结果，不是最终采购结论，不代表真实采购已经完成。

阶段 4 页面、文档和代码命名统一使用：

- 规则响应
- 规则排序结果
- 候选商品 Top 3
- 本地规则排序候选商品

不使用：

- 真实推荐结果
- 最终推荐
- 最终采购结论

## 2. 允许新增和修改文件

允许新增：

- `STAGE4_PLAN.md`
- `src/response_builder.py`

允许修改：

- `app.py`
- `src/doc_writer.py`

允许运行时生成：

- `outputs/responses.json`
- `outputs/output.docx`

阶段 4 验收通过后再新增：

- `STAGE4_SUMMARY.md`

## 3. 禁止事项

阶段 4 仍然禁止：

- 爬虫。
- AI。
- 数据库。
- 登录。
- 真实采购。
- 自动下单。
- 阶段 5 搜索增强。
- 多平台真实数据抓取。
- 店铺真实性判断。
- 库存真实性判断。
- 修改阶段 3 的评分、尺寸识别、材质匹配或服务匹配规则。
- 把阶段 4 产物描述为最终采购结论。

## 4. `src/response_builder.py` 设计

新增 `src/response_builder.py`，负责把阶段 3 的排序结果转成阶段 4 的规则响应。

### 4.1 `select_top_products(ranked_products, top_n=3)`

职责：

- 从排序结果中选择最多 3 个候选商品。
- 只排除明显无关商品。
- 过滤后不足 3 个候选商品时，允许返回实际数量。
- 如果没有任何可用候选商品，返回空列表，由页面清晰提示，不生成错误 Word。

明显无关商品包括：

- 标题与采购需求完全不相关。
- 风险提示中包含明显无关。
- 分数明显低且商品类型不符。

普通风险不能直接排除，例如：

- 材质需人工复核。
- 服务未明确。
- 尺寸需人工复核。

汇总表不能包含明显无关商品，例如电热水壶。

### 4.2 `build_recommendation_responses(requirements, ranked_products, top_n=3)`

职责：

- 先调用 `select_top_products(ranked_products, top_n=3)` 选择候选商品。
- 使用 Top 1 作为第一候选商品。
- 基于 Top 1 的 `title`、`specs_text`、`service_text`、`raw_text` 生成每一条技术参数的 `response_value`。
- Top 2 和 Top 3 只作为备选写入汇总表，不参与逐项参数响应生成。

证据约束：

- 只有 Top 1 商品文本中能明确支持的参数，才写明确响应。
- 无法确认的参数必须写：`需人工复核：第一候选商品文本未明确确认……`
- 禁止编造颜色、防火等级、厚度、密度、环保等级、质保年限、安装服务等商品文本未明确出现的信息。

### 4.3 `outputs/responses.json` 字段

`outputs/responses.json` 每条至少包含：

- `index`
- `name`
- `unit`
- `required_value`
- `response_value`
- `source_product_title`
- `evidence`
- `review_required`

## 5. `src/doc_writer.py` 修改要求

修改 `src/doc_writer.py` 时必须保持旧接口兼容。

原有调用方式必须继续可用：

```python
write_responses(input_path, responses, output_path)
```

新增可选参数：

```python
write_responses(input_path, responses, output_path, summary_products=None)
```

行为要求：

- `summary_products is None` 时，只执行原来的参数响应写回。
- `summary_products` 有候选商品时，才在 Word 末尾追加汇总表。
- 不能破坏阶段 1 模拟响应写回能力。

Word 汇总表标题必须固定为：

```text
候选商品 Top 3（本地规则排序候选商品，非最终采购结论）
```

汇总表字段：

- 排名
- 商品名称
- 平台
- 价格
- 链接
- 匹配分数
- 匹配理由
- 风险提示

## 6. `app.py` 修改要求

按钮文案改为：

```text
生成规则响应并导出 Word
```

点击按钮时：

- 优先使用当前页面流程中刚生成的 `ranked_products`。
- 不盲目依赖旧 `outputs/ranked_products.json`，避免旧排序结果被写回 Word。
- 仅当 `requirements_valid`、商品加载成功、当前排序结果有效时允许生成。
- 如果 `select_top_products(...)` 返回空列表，页面提示“没有可用候选商品，暂不能生成 Word”，不生成错误 Word。
- 成功后生成 `outputs/responses.json`。
- 调用 `write_responses(..., summary_products=top_products)` 输出 `outputs/output.docx`。
- 下载按钮继续沿用当前“本次生成成功 + 上传 key 一致 + 文件存在”的保护逻辑。

## 7. 命令行运行要求

`src.response_builder` 必须支持：

```bash
python -m src.response_builder
```

命令行运行时读取：

- `outputs/requirements.json`
- `outputs/ranked_products.json`

成功后输出：

- `requirements` 数量
- Top 候选商品数量
- `responses` 数量
- `responses.json` 保存路径

如果 `requirements.json` 或 `ranked_products.json` 缺失，要给出清晰提示，不要抛长堆栈。

## 8. 测试计划

一次性命令验收：

```powershell
python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('app.py syntax ok')"
python -m src.product_loader
python -m src.product_ranker
python -m src.response_builder
python -m json.tool outputs/responses.json
```

旧接口回归验收：

- 用旧调用方式单独验证 `write_responses(input_path, responses, output_path)` 仍可生成 Word。
- 确认 `summary_products=None` 时不会追加候选商品汇总表。

Streamlit 手动验收：

1. 上传样例 Word 后仍解析 13 条技术参数。
2. 本地候选商品仍展示 8 条。
3. 规则排序结果仍展示 8 条。
4. 点击“生成规则响应并导出 Word”后使用当前页面排序结果生成 `output.docx`。
5. Word 中“投标人响应值”列不为空。
6. 无法确认的参数包含“需人工复核”。
7. Word 末尾出现固定标题的候选商品汇总表。
8. 汇总表最多 3 条，允许少于 3 条，但不能包含明显无关商品，例如电热水壶。
9. 若过滤后没有可用候选商品，页面提示清晰且不生成 Word。

## 9. 阶段完成标准

阶段 4 完成需要同时满足：

- `python -m src.response_builder` 可运行。
- `outputs/responses.json` 可生成并通过 JSON 校验。
- `app.py` 使用当前页面刚生成的排序结果生成 Word。
- `write_responses(input_path, responses, output_path)` 旧接口仍可用。
- `write_responses(..., summary_products=top_products)` 可追加候选商品汇总表。
- `outputs/output.docx` 可以打开。
- Word 技术参数表的“投标人响应值”列已写入规则响应。
- Word 末尾包含“候选商品 Top 3（本地规则排序候选商品，非最终采购结论）”汇总表。
- 汇总表不包含明显无关商品。
- 未进入阶段 5。

## 10. 风险和兜底

- 如果 Top 1 商品文本无法确认某项参数，必须写“需人工复核”，不补造参数。
- 如果 Top 3 过滤后不足 3 个，写入实际数量。
- 如果没有可用候选商品，页面提示并停止生成 Word。
- 如果商品读取失败，只影响候选商品、排序和阶段 4 导出，不影响 Word 上传解析。
- 如果输出 Word 被 Word 或 WPS 占用，页面应显示写出失败信息，用户关闭文件后重试。
