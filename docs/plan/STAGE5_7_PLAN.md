# 阶段 5-7 实施计划

## 一、当前项目状态判断

- 阶段 1-4 已有验收文档与核心代码：Word 解析、Word 写回、本地商品读取、规则排序、Top 3 汇总与规则响应生成均已存在。
- 本阶段只做增量集成，不重做阶段 2-4，不接入爬虫、数据库、后端服务、GUI 或 AI API。
- `app.py` 继续使用 `load_products(path)`、`rank_products(products, requirements)` 和 `write_responses(..., summary_products=top_products)`，这些接口必须保持兼容。
- `data/products.json` 保留为阶段 2-4 的本地商品数据；新增 `data/sample_products.json` 仅用于阶段 5-7 本地端到端验证。

## 二、阶段 5：候选商品读取与标准化

计划内容：

1. 新增 `data/sample_products.json`，明确标记为本地测试数据、非真实平台爬取结果。
2. 增量完善 `src/product_loader.py`：
   - 保留 `load_products(path)`。
   - 新增 `load_products_json(path)`。
   - 新增 `normalize_product(product)`。
   - 新增 `normalize_products(products)`。
   - 新增 `validate_product(product)`。
3. 标准化字段覆盖：
   - `product_id,title,brand,category,price,material,color,dimensions,style,source,url,notes,specs_text,service_text,raw_text`
   - 同时保留阶段 2-4 已使用的 `platform,shop,image_url` 等字段，保证 Streamlit 页面和旧 JSON 可继续工作。
4. 字段缺失时填默认空值或 `None`，不因缺字段崩溃。

## 三、阶段 6：评分与排序

计划内容：

1. 增量完善 `src/product_ranker.py`，继续使用本地规则评分。
2. 保留主接口 `rank_products(products, requirements)`。
3. 支持 `score_product(requirements, product)`，同时兼容旧的 `score_product(product, requirements)` 调用方式。
4. 新增 `explain_score(requirements, product, score_detail)`。
5. 评分维度覆盖：类目、价格、材质、颜色、尺寸或规格、风格或关键词，并保留阶段 3 已有标题、服务、完整度、明显无关商品惩罚逻辑。
6. 排序结果继续保留 `score,reasons,risks`，并增补 `total_score,score_detail,reason`。

## 四、阶段 7：端到端主流程

计划内容：

1. 新增 `main.py`。
2. 默认读取 `data/办公屏风01模板样例.docx`。
3. 输出统一写入 `outputs/`：
   - `outputs/requirements.json`
   - `outputs/ranked_products.json`
   - `outputs/responses.json`
   - `outputs/recommendation_result.docx`
4. 默认 Word 不存在时返回清晰错误。
5. 使用阶段 4 的 `response_builder.py` 和 `doc_writer.py`，不破坏既有 Word 写回接口。

## 五、验证计划

必须运行：

```powershell
python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('app.py syntax ok')"
python -m src.product_loader
python -m src.product_ranker
python -m src.response_builder
python main.py
python -m json.tool outputs/ranked_products.json
python -m json.tool outputs/responses.json
python -c "from src.product_loader import load_products; from src.product_ranker import rank_products; from src.doc_writer import write_responses; print('legacy imports ok')"
```

如新增测试：

```powershell
python -m pytest tests
```

## 六、边界说明

- 本阶段输出仍为本地规则推荐与候选商品响应，不是最终采购结论。
- `data/sample_products.json` 只作为本地测试候选数据，不能代表真实爬取、真实库存、真实价格或真实采购可行性。
