# 采购商品推荐系统快速上手与改动指南

更新时间：2026-06-01

这份文档给后来接手项目的人用：先知道系统做什么，再知道怎么跑起来，最后知道常见需求应该改哪里。

## 1. 一句话理解项目

本项目现在的主目标是：

用户输入采购指标，系统按 GoodsSpider 风格打开淘宝、京东搜索商品，解析商品信息，按采购指标筛选排序，展示推荐商品，并导出 JSON、CSV，必要时写回 Word 文档。

主流程可以理解为：

```text
采购指标输入
  -> 生成搜索关键词
  -> 淘宝/京东搜索商品
  -> 解析商品标题、价格、店铺、销量、图片、链接
  -> 按采购指标打分排序
  -> 展示 Top 推荐商品
  -> 导出 JSON / CSV / DOCX
```

## 2. 先看哪些文件

新接手时，建议按这个顺序看：

1. `docs/GFoodsSpider_SUMMARY.md`

   了解这次 GoodsSpider 改造做了什么、做到哪里、还有哪些限制。

2. `ui_streamlit.py`

   当前客户看到的网页入口。主页面、按钮、下载区、人工登录提示都在这里。

3. `main.py`

   业务编排入口。采购指标、淘宝/京东搜索、排序、输出文件都在这里串起来。

4. `src/marketplace_spider.py`

   GoodsSpider 风格 Selenium 搜索实现，负责打开淘宝/京东、解析页面、识别登录或风控。

5. `src/crawler/adapters/taobao_search_adapter.py`

   淘宝搜索结果解析适配器，支持解析淘宝搜索 HTML / JSON 导出文件。

6. `src/product_ranker.py`

   商品打分排序规则。

7. `src/doc_parser.py` 和 `src/doc_writer.py`

   Word 采购指标解析和推荐结果写回 Word。

8. `tests/test_stage16_taobao_procurement_recommendation.py`

   本次淘宝/京东采购推荐能力的主要验收测试。

## 3. 本地运行

先安装依赖：

```powershell
python -m pip install -r requirements.txt
```

启动当前主页面：

```powershell
python -m streamlit run ui_streamlit.py --server.port 8501
```

浏览器打开：

```text
http://127.0.0.1:8501/
```

注意：

- `ui_streamlit.py` 是当前主入口。
- `app.py` 是早期 Word 闭环演示入口，不是当前客户主页面。
- 淘宝、京东线上搜索可能触发登录、验证码、风控。遇到这种情况，页面里勾选“淘宝要求登录/验证时，打开浏览器人工登录”后再试。

## 4. 页面怎么用

当前客户主流程在首页：

1. 在“采购指标”里输入采购要求。

   示例：

   ```text
   尺寸要求：1600×750×750mm
   主体材质：钢制框架 + 实木颗粒板面板
   配送及安装要求：配送至指定地点，包安装
   ```

2. 填写“淘宝搜索关键词”。

   示例：

   ```text
   办公屏风工位 1600x750x750 钢制 包安装
   ```

3. 需要京东一起搜，就勾选“同时搜索京东”。

4. 如果淘宝提示登录或验证码，就勾选“淘宝要求登录/验证时，打开浏览器人工登录”。

5. 点击“搜索并生成推荐数据”。

6. 查看推荐商品表，并下载结果文件。

输出通常在：

```text
outputs/taobao_procurement_recommendations/
outputs/marketplace_doc_recommendations/
```

## 5. 核心流程在哪里

### 首页按钮逻辑

文件：

```text
ui_streamlit.py
```

重点函数：

```text
_render_main_procurement_workflow
run_taobao_procurement_recommendation_action
_render_procurement_result
_top_product_rows
_render_file_downloads
```

如果要改页面字段、按钮、提示文案、下载按钮，优先改这里。

### 指标输入到推荐数据

文件：

```text
main.py
```

重点函数：

```text
run_taobao_procurement_recommendation
```

它负责：

- 把用户输入的采购指标解析成结构化 requirements。
- 生成淘宝搜索关键词和搜索链接。
- 调用 Selenium 搜索或导入淘宝搜索结果文件。
- 保存候选商品 JSON。
- 调用排序规则。
- 生成推荐结果 JSON、评分 CSV、responses JSON。

### Word 上传到 Word 输出

文件：

```text
main.py
```

重点函数：

```text
run_marketplace_doc_recommendation
```

它负责：

- 解析用户上传的采购 Word。
- 搜索淘宝/京东。
- 排序推荐商品。
- 写出新的 `recommendation_result.docx`。

## 6. 商品搜索怎么改

文件：

```text
src/marketplace_spider.py
```

重点位置：

```text
GoodsSpiderStyleMarketplaceSpider
parse_jingdong_search_results
is_taobao_blocked
is_jingdong_login_required
_make_driver
```

常见改动：

- 淘宝页面结构变了：改淘宝商品卡片解析逻辑。
- 京东页面结构变了：改 `parse_jingdong_search_results`。
- 想多翻页：调整调用时的 `pages`。
- 想限制数量：调整调用时的 `max_items`。
- 想人工登录：运行时让 `headless=False`，页面上对应“人工登录模式”。

安全边界：

- 不保存账号密码。
- 不保存 Cookie。
- 不绕过验证码。
- 不注入平台风控绕过脚本。

## 7. 排序规则怎么改

文件：

```text
src/product_ranker.py
src/sourcing_assistant.py
```

重点函数：

```text
rank_products
score_product
explain_score
enrich_ranked_products_with_sourcing_guidance
```

常见改法：

- 想让价格更重要：改 `score_product` 中价格相关得分。
- 想让尺寸更重要：改尺寸匹配相关逻辑。
- 想加材质、安装服务、销量、店铺信用权重：在 `score_product` 中加分或扣分。
- 想让推荐理由更清楚：改 `explain_score` 或 `enrich_ranked_products_with_sourcing_guidance`。

改完排序规则后，重点跑：

```powershell
python -m unittest tests.test_stage16_taobao_procurement_recommendation
```

## 8. 下载结果怎么改

结构化输出主要在：

```text
outputs/taobao_procurement_recommendations/
```

相关代码：

```text
main.py
src/sourcing_assistant.py
ui_streamlit.py
```

常见输出文件：

```text
recommended_products.json
sourcing_score_table.csv
ranked_products.json
taobao_candidates.json
responses.json
```

如果客户说“下载表格列不对”：

1. 先看 `src/sourcing_assistant.py` 的 `write_scoring_csv` 和 `build_scoring_table_rows`。
2. 再看 `main.py` 返回的 `downloadable_files`。
3. 最后看 `ui_streamlit.py` 的 `_render_file_downloads`。

如果客户说“页面上表格列不对”：

1. 改 `ui_streamlit.py` 的 `_top_product_rows`。

## 9. Word 解析和回填怎么改

Word 解析：

```text
src/doc_parser.py
```

Word 写回：

```text
src/doc_writer.py
```

常见改法：

- 客户 Word 模板表头变了：改 `doc_parser.py` 的表头识别逻辑。
- 要把推荐商品写到指定表格：改 `doc_writer.py` 的 `write_responses`。
- 要增加“推荐理由、风险提示、价格、店铺、链接、图片链接”：改 `doc_writer.py` 中的格式化函数。
- 要新增交付摘要：改 `doc_writer.py` 的 `_append_delivery_report` 相关函数。

## 10. 淘宝线上搜不到怎么办

这是预期风险，不一定是代码坏了。淘宝、京东经常要求登录、验证码或触发风控。

排查顺序：

1. 页面是否提示“登录、验证码、风控验证”。
2. 勾选“人工登录模式”后重试。
3. 降低搜索速度，减少页数和数量。
4. 用 `data/stage16_taobao_search_demo.html` 跑离线解析，确认排序和输出链路正常。
5. 如果客户要稳定生产使用，应接授权 API、企业采购平台或客户允许的数据导出文件。

离线演示可用文件：

```text
data/stage16_taobao_search_demo.html
```

它用于证明“解析、排序、输出”链路可运行，不依赖真实淘宝页面。

## 11. 常见需求改动对照表

| 客户需求 | 优先改的文件 | 重点函数 |
| --- | --- | --- |
| 改首页文案、按钮、表单字段 | `ui_streamlit.py` | `_render_main_procurement_workflow` |
| 改推荐商品展示列 | `ui_streamlit.py` | `_top_product_rows` |
| 改下载按钮和下载文件 | `ui_streamlit.py`, `main.py` | `_render_file_downloads`, `downloadable_files` |
| 改淘宝搜索关键词生成 | `src/sourcing_assistant.py` | `generate_sourcing_keywords` |
| 改淘宝搜索解析 | `src/crawler/adapters/taobao_search_adapter.py`, `src/marketplace_spider.py` | `parse_taobao_search_results` |
| 改京东搜索解析 | `src/marketplace_spider.py` | `parse_jingdong_search_results` |
| 改打分排序 | `src/product_ranker.py` | `score_product`, `rank_products` |
| 改推荐理由和风险提示 | `src/product_ranker.py`, `src/sourcing_assistant.py` | `explain_score`, `enrich_ranked_products_with_sourcing_guidance` |
| 改 Word 读取 | `src/doc_parser.py` | `parse_requirements` |
| 改 Word 输出 | `src/doc_writer.py` | `write_responses` |
| 新增平台，比如 1688 | `src/marketplace_spider.py`, `main.py`, `ui_streamlit.py` | 平台 parser、sites 参数、页面选项 |

## 12. 修改后怎么验收

基础测试：

```powershell
python -m unittest discover -s tests -p test*.py
```

编译检查：

```powershell
python -m py_compile main.py ui_streamlit.py src\marketplace_spider.py src\crawler\adapters\taobao_search_adapter.py src\sourcing_assistant.py
```

只测本次 GoodsSpider 改造：

```powershell
python -m unittest tests.test_stage16_taobao_procurement_recommendation
```

页面检查：

```powershell
python -m streamlit run ui_streamlit.py --server.port 8501
```

然后打开：

```text
http://127.0.0.1:8501/
```

验收时至少确认：

- 首页能打开。
- 输入采购指标后能点击生成。
- 淘宝风控时页面能给出明确错误，不会乱推荐无关商品。
- 离线淘宝 demo 可以生成推荐 JSON 和 CSV。
- 修改排序后，测试仍然通过。
- 下载文件能正常打开。

## 13. 开发注意事项

- 线上淘宝、京东抓取结果不稳定，不要把一次真实搜索失败直接判断为系统整体失败。
- 采购推荐结果只是辅助候选，价格、库存、店铺资质、发票、配送安装需要人工复核。
- 不要把账号密码、Cookie、浏览器用户数据提交进项目。
- `outputs/` 是运行产物，不要把它当作核心代码依赖。
- `data/` 是样例数据和测试输入，改动前确认测试是否依赖。
- 改 UI 后要实际打开页面看一眼，防止页面能跑但客户不知道怎么用。

## 14. 最快改动路线

如果只想快速完成一个客户反馈，按这个路线走：

1. 先复现：打开 `http://127.0.0.1:8501/` 看客户说的问题。
2. 判断类型：
   - 页面问题：改 `ui_streamlit.py`。
   - 搜索问题：改 `src/marketplace_spider.py` 或淘宝 adapter。
   - 排序问题：改 `src/product_ranker.py`。
   - Word 问题：改 `src/doc_parser.py` 或 `src/doc_writer.py`。
3. 用 `data/stage16_taobao_search_demo.html` 做离线验证。
4. 跑 Stage16 测试。
5. 跑全量测试。
6. 再打开页面手工检查一遍。
