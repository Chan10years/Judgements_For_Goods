# 阶段 3 计划：匹配排序闭环

## 1. 阶段目标

阶段 3 只实现本地规则评分排序闭环：根据 Word 解析出的采购参数 `requirements` 和 `data/products.json` 中的候选商品 `products`，生成每个商品的 `score`、`reasons`、`risks`，并在 Streamlit 页面展示排序结果。

阶段 3 允许运行时生成 `outputs/ranked_products.json`。该文件是阶段 3 的中间排序产物，只用于页面展示和后续阶段读取，不代表最终采购结论，不能写回 Word，也不能替代阶段 4 的正式响应生成逻辑。

## 2. 允许修改文件

- 新增 `STAGE3_PLAN.md`
- 新增 `src/product_ranker.py`
- 修改 `app.py`

阶段 3 验收后再新增 `STAGE3_SUMMARY.md`。

## 3. 禁止事项

- 不做爬虫。
- 不做 AI 生成。
- 不做数据库。
- 不做登录。
- 不做真实采购。
- 不生成 `responses.json`。
- 不把真实商品响应写回 Word。
- 不追加 Word 推荐商品汇总表。
- 不重构项目结构。
- 不引入新的前端框架。
- 不修改 `PROJECT_CONTROL.md`、`FLOW.md`、`TASKS.md`、`STAGE1_PLAN.md`、`STAGE1_SUMMARY.md`、`STAGE2_PLAN.md`、`STAGE2_SUMMARY.md`。
- 不修改 `src/doc_parser.py`、`src/doc_writer.py`、`src/mock_response.py`、`src/product_loader.py`，除非发现明确阻断 bug。
- 不修改 `data/products.json`，除非发现格式阻断问题。

Streamlit 页面文案涉及排序时只使用“规则排序结果”“候选商品排序”“本地规则匹配结果”，不使用“推荐商品”“智能推荐”“最佳推荐”“最终推荐”。

## 4. 字段策略说明

阶段 3 采用严格字段完整策略。`products.json` 中商品字段必须齐全，缺字段时由 `product_loader.py` 报错并在页面展示错误，不进入评分排序。

阶段 3 不回头重写 `product_loader.py` 的缺字段补齐策略。

`src/product_ranker.py` 提供内部辅助函数 `collect_requirement_text(requirements)`，兼容 `str`、`list`、`dict`，用于把 Word 解析出的参数名称、参数值、原始文本合并成统一文本，供数字、尺寸、材质、服务关键词匹配使用。

## 5. 评分规则

每个商品总分范围为 0 到 100。

- 标题相关度，最多 25 分：标题包含“办公屏风”“工位”“隔断”等关键词加分。
- 尺寸匹配度，最多 20 分：商品文本包含采购参数中的尺寸数字，例如 `1600`、`750` 等，加分。
- 材质匹配度，最多 15 分：商品文本包含“钢制”“颗粒板”“板材”“玻璃”“框架”等关键词加分。
- 服务匹配度，最多 10 分：`service_text` 中包含“配送”“安装”“售后”“质保”等关键词加分。
- 参数完整度，最多 10 分：`specs_text`、`service_text`、`raw_text`、`url`、`price` 越完整，加分越高。
- 价格合理性，最多 10 分：`price` 是数字且处于常见办公家具合理区间时加分。
- 风险扣分，最多扣 10 分：标题弱相关、尺寸缺失、材质缺失、服务缺失、价格缺失、明显无关商品等进入 `risks`。

## 6. 输出结构

排序结果每条商品至少包含：

- 原商品字段
- `score`：数字，范围 0 到 100
- `reasons`：列表，说明加分原因
- `risks`：列表，说明风险或需人工复核点

`outputs/ranked_products.json` 使用 UTF-8 JSON 保存，`ensure_ascii=False`，便于页面展示和后续阶段读取。

## 7. 页面展示方式

- 保留阶段 1 Word 上传、`parse_requirements`、`save_requirements_json`、`build_mock_responses`、`write_responses`、`output.docx` 下载流程。
- 保留阶段 2 本地候选商品展示。
- 用户上传 Word 并成功解析 `requirements` 后，调用 `rank_products(products, requirements)`。
- 页面新增“规则排序结果”区块，展示“本地规则匹配结果”。
- 商品按 `score` 从高到低展示。
- 页面展示 `score`、`title`、`platform`、`price`、`shop`、`url`、`reasons`、`risks`。
- 如果没有上传 Word，只提示“上传 Word 后可生成规则排序结果”，不要报错。
- 商品读取失败时，只影响候选商品和排序区，不影响阶段 1 Word 闭环。

## 8. 命令行运行要求

`src/product_ranker.py` 必须支持：

```bash
python -m src.product_ranker
```

运行时读取 `data/products.json` 和 `outputs/requirements.json`。

如果 `outputs/requirements.json` 不存在，要给出清晰提示，不输出堆栈，不崩溃。

成功运行后输出：

- 商品总数
- 排序商品总数
- 第一名商品标题
- 最高分
- 最低分
- `ranked_products.json` 保存路径

## 9. 验收标准

- `python -m src.product_loader` 仍然通过。
- Streamlit 页面仍能上传样例 Word。
- 样例 Word 仍能解析出 13 条技术参数。
- 阶段 1 模拟响应导出功能仍保留。
- 本地候选商品仍能展示 8 条。
- 上传 Word 后页面能展示规则排序结果。
- 每个商品都有 `score`、`reasons`、`risks`。
- 商品按 `score` 从高到低排列。
- 办公屏风相关商品排在无关商品前面。
- `outputs/ranked_products.json` 能生成，内容为 UTF-8 JSON。
- 未出现爬虫、AI、数据库、登录、真实 Word 推荐写回、`responses.json`、推荐商品汇总表。

## 10. 测试计划

- 运行 `python -m src.product_loader`，确认商品字段检查通过。
- 运行 `python -m src.product_ranker`，确认排序命令行输出完整。
- 使用样例 Word 检查 `parse_requirements` 仍解析出 13 条技术参数。
- 检查 `outputs/ranked_products.json` 是否生成、是否为 UTF-8 JSON、是否包含 8 条排序结果。
- 检查排序结果中每条商品是否包含 `score`、`reasons`、`risks`。
- 检查分数是否按从高到低排列，办公屏风相关商品是否排在电热水壶等明显无关商品前。
- 通过 Streamlit 页面人工验证 Word 闭环、本地候选商品展示、规则排序结果展示。

## 11. 风险和兜底

- 商品字段缺失：继续由 `product_loader.py` 报错，页面展示错误，不进入排序。
- `outputs/requirements.json` 不存在：命令行给出清晰提示；页面在未上传 Word 时提示上传后生成规则排序结果。
- 规则评分只能作为阶段 3 中间排序依据，不作为最终采购结论。
- 排序结果不写回 Word，不影响阶段 1 模拟响应导出。
