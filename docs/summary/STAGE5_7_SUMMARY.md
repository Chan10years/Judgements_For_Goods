# 阶段 5-7 总结：候选商品标准化、规则评分排序与端到端主流程

## 1. 阶段 5-7 目标

阶段 5-7 的目标是做增量集成，打通从默认 Word 需求文档到本地候选商品读取、商品标准化、规则评分排序、Top 3 规则推荐、规则响应生成和 Word 写回的端到端流程。

本阶段基于阶段 1-4 已验收能力继续推进，不重做阶段 2-4，不破坏旧接口，不修改已验收的 Streamlit 页面能力。

阶段 5-7 输出仍为本地测试数据和本地规则推荐结果，不是最终采购结论，不代表真实采购已经完成。

## 2. 本阶段新增和修改文件

新增文件：

- `STAGE5_7_PLAN.md`
- `STAGE5_7_SUMMARY.md`
- `data/sample_products.json`
- `main.py`
- `tests/test_stage5_7.py`
- `outputs/recommendation_result.docx`

修改文件：

- `src/product_loader.py`
- `src/product_ranker.py`
- `outputs/requirements.json`
- `outputs/ranked_products.json`
- `outputs/responses.json`

说明：

- `data/products.json` 未删除、未替换，仍保留为阶段 2-4 本地商品数据。
- `data/sample_products.json` 仅作为阶段 5-7 本地测试候选商品数据，已明确标记为非真实平台爬取结果。
- `outputs/requirements.json`、`outputs/ranked_products.json`、`outputs/responses.json`、`outputs/recommendation_result.docx` 为端到端运行产物。
- 阶段 5-7 原则上未修改 `app.py`，继续保持阶段 1-4 已验收页面能力。

## 3. 阶段 5 完成功能说明

已完成 `data/sample_products.json`：

- 提供 6 条本地测试候选商品。
- 包含办公屏风相关候选商品、缺字段候选商品和明显无关商品样例。
- 所有样例均标记为本地测试数据，未伪装成真实爬取结果。

已完成 `src/product_loader.py` 增量完善：

- 保留旧接口：`load_products(path)`。
- 新增 `load_products_json(path)`。
- 新增 `normalize_product(product)`。
- 新增 `normalize_products(products)`。
- 新增 `validate_product(product)`。
- 标准化字段覆盖 `product_id,title,brand,category,price,material,color,dimensions,style,source,url,notes,specs_text,service_text,raw_text`。
- 同时保留阶段 2-4 已使用的 `platform,shop,image_url` 等字段，保证旧页面和旧数据结构继续可用。
- 字段缺失时使用空字符串或 `None` 兜底，不因缺字段崩溃。

## 4. 阶段 6 完成功能说明

已完成 `src/product_ranker.py` 增量完善：

- 保留主接口：`rank_products(products, requirements)`。
- 新增并支持 `score_product(requirements, product)`。
- 兼容旧调用顺序 `score_product(product, requirements)`。
- 新增 `explain_score(requirements, product, score_detail)`。
- 继续使用本地规则评分，未接入 AI。
- 评分维度覆盖类目、价格、材质、颜色、尺寸或规格、风格或关键词。
- 保留阶段 3 已有标题、服务、完整度、明显无关商品惩罚等规则思路。
- 每个排序商品继续保留 `score`、`reasons`、`risks`。
- 新增 `total_score`、`score_detail`、`reason`，但未替代旧字段。
- 排序输出继续可被阶段 4 的 `response_builder.py` 接收。

## 5. 阶段 7 完成功能说明

已完成 `main.py`：

- 默认读取 Word：`data/办公屏风01模板样例.docx`。
- 解析需求并保存 `outputs/requirements.json`。
- 读取 `data/sample_products.json`。
- 标准化候选商品。
- 执行规则评分排序。
- 保存 `outputs/ranked_products.json`。
- 选择 Top 3 候选商品。
- 生成规则响应。
- 保存 `outputs/responses.json`。
- 写回 Word 输出 `outputs/recommendation_result.docx`。
- 默认 Word 或本地测试商品 JSON 不存在时，返回清晰错误提示。
- 调用 `write_responses(..., summary_products=top_products)`，未破坏 `write_responses(input_path, responses, output_path)` 旧接口。

## 6. 自动验证命令与结果

已运行以下命令：

```powershell
python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('app.py syntax ok')"
```

结果：通过，输出 `app.py syntax ok`。

```powershell
python -m src.product_loader
```

结果：通过，可读取 `data/products.json` 和 `data/sample_products.json`，字段检查通过。

```powershell
python -m src.product_ranker
```

结果：通过，可完成商品排序并保存 `outputs/ranked_products.json`。

```powershell
python -m src.response_builder
```

结果：通过，输出 requirements 数量 `13`，Top 候选商品数量 `3`，responses 数量 `13`。

```powershell
python main.py
```

结果：通过，端到端流程完成，输出 requirements 数量 `13`、候选商品数量 `6`、排序商品数量 `6`、Top 候选商品数量 `3`、responses 数量 `13`。

```powershell
python -m json.tool outputs/ranked_products.json
python -m json.tool outputs/responses.json
```

结果：通过，两个 JSON 文件均可被 JSON 工具校验。

```powershell
python -c "from src.product_loader import load_products; from src.product_ranker import rank_products; from src.doc_writer import write_responses; print('legacy imports ok')"
```

结果：通过，输出 `legacy imports ok`。

```powershell
python -m unittest discover tests
```

结果：通过，6 个测试全部 OK。

说明：当前环境未安装 `pytest`，因此新增测试使用标准库 `unittest` 覆盖阶段 5-7 建议验收项。

## 7. Word 输出检查结果

已对 `outputs/recommendation_result.docx` 做只读检查：

- 文件存在，且可被 `python-docx` 打开。
- Word 文档包含候选商品 Top 3 汇总标题：`候选商品 Top 3（本地规则排序候选商品，非最终采购结论）`。
- Word 文档共有 2 个表格。
- 候选商品汇总表不包含 `电热水壶`。
- Top 3 汇总来源于本地规则排序候选商品，不是最终采购结论。

## 8. 手动验收结果

用户已确认阶段 5-7 手动验收通过。

手动验收重点包括：

- 命令可正常运行。
- 端到端流程可生成所有要求产物。
- JSON 输出可解析。
- Word 输出可打开。
- Top 3 汇总存在。
- 明显无关商品未进入 Top 3 汇总。
- 本地测试商品未被描述为真实来源。
- 规则推荐结果未被称为最终采购结论。

## 9. 阶段边界确认

阶段 5-7 未接入：

- 真实爬虫
- 淘宝、京东、1688、得物等真实平台
- AI API
- 数据库
- 后端服务
- 新 GUI
- 登录系统
- 真实采购
- 自动下单

阶段 5-7 没有删除或替换 `data/products.json`。

阶段 5-7 没有破坏：

- `load_products(path)`
- `rank_products(products, requirements)`
- `write_responses(input_path, responses, output_path)`
- `write_responses(..., summary_products=top_products)`

## 10. 残余风险

- 当前排序和响应仍依赖本地规则与本地测试商品文本，不能替代真实采购判断。
- `data/sample_products.json` 只用于本地流程验证，不代表真实商品、真实库存、真实价格或真实采购可行性。
- 部分需求项如承重、环保、五金件、连接结构等缺少本地测试商品的明确证据，响应中会提示需人工复核。
- `pytest` 未安装，本阶段测试使用 `unittest` 完成。

## 11. 最终结论

阶段 5-7 已完成。

验收结论：通过。

当前项目已打通从默认 Word 需求文档到本地测试候选商品读取、商品标准化、规则评分排序、Top 3 规则推荐、规则响应生成和 Word 写回的端到端流程。

阶段 5-7 结果仅为本地规则排序候选商品和本地规则响应，不是最终采购结论，未接入爬虫、AI、数据库、后端服务、真实平台、真实采购或自动下单。
