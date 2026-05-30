# 阶段14总结：V2-A 浏览器辅助式淘宝/京东寻源 MVP

## 修改文件列表

新增：

1. `STAGE14_V2A_PLAN.md`
2. `STAGE14_V2A_SUMMARY.md`
3. `tests/test_stage14_v2a_sourcing_flow.py`
4. `data/stage14_candidate_links_demo.txt`
5. `data/stage14_candidate_products_demo.csv`

小改：

1. `TASKS.md`
2. `ui_streamlit.py`
3. `main.py`

本阶段未实际修改 `src/product_loader.py`、`src/product_ranker.py` 和 `src/doc_writer.py` 的阶段14逻辑；`src/doc_writer.py` 保持阶段13.2B 已有的 Word 推荐表增强能力。

## V2-A 功能说明

阶段14 已把系统从“上传候选商品文件后推荐”升级为“浏览器辅助式淘宝/京东寻源”：

1. 系统根据采购 Word 指标生成淘宝/京东搜索关键词和搜索链接。
2. 客户在自己的浏览器中正常登录淘宝/京东。
3. 客户人工查看并确认候选商品。
4. 客户导入候选商品 CSV/JSON，或导入候选链接清单 TXT。
5. 系统标准化候选商品字段。
6. 系统对缺失字段标记待人工复核。
7. 系统复用现有规则排序，显示 Top 推荐。
8. 系统输出并下载 Word 推荐报告。
9. 页面额外提供候选商品 JSON 和排序结果 JSON 下载。

## 客户使用流程

1. 运行 `streamlit run ui_streamlit.py`。
2. 在 V2-A 区块上传采购 Word。
3. 查看系统生成的淘宝/京东搜索词和搜索链接。
4. 客户在自己的浏览器中正常登录淘宝/京东并打开搜索入口。
5. 客户人工确认候选商品。
6. 客户上传候选商品 CSV/JSON，或上传候选链接清单 TXT。
7. 点击“生成推荐 Word”。
8. 查看需求数量、候选商品数量、Top 推荐数量和输出 Word 路径。
9. 查看页面 Top 推荐商品表。
10. 下载 Word 报告、候选商品 JSON 和排序结果 JSON。

## 候选链接清单能力

候选链接清单支持 `.txt`：

1. 一行可包含一个淘宝、天猫或京东链接。
2. 同一行可附带客户人工确认的商品名称、价格、尺寸、材质、安装服务等文本。
3. 系统只解析客户主动提供的文本，不访问淘宝/京东页面。
4. 纯链接会生成待人工复核候选记录，标题、价格、尺寸、材质、安装服务等缺失字段不会被编造。

演示文件：`data/stage14_candidate_links_demo.txt`。

## 不做事项

本阶段没有做强抓淘宝/京东搜索页，没有保存淘宝/京东账号密码或 Cookie，没有绕验证码和风控，没有使用代理池，没有自动下单，没有抓取个人信息，没有承诺最终采购结论。

## 测试命令与结果

已执行：

1. `python -m py_compile main.py`：通过。
2. `python -m py_compile ui_streamlit.py`：通过。
3. `python -m py_compile src/doc_writer.py`：通过。
4. `python -m unittest tests.test_stage14_v2a_sourcing_flow`：通过，7 个测试 OK。
5. `python -m unittest tests.test_stage13_2b_delivery_mvp`：通过，11 个测试 OK。
6. `python -m unittest discover tests`：通过，71 个测试 OK。
7. `python main.py`：通过，固定路径端到端仍生成 `outputs/recommendation_result.docx`。
8. `git status --short`：已查看。

## 禁止文件审计

审计命令 `git diff --name-only -- app.py src\crawler\fetcher.py src\crawler\parser.py src\crawler\pipeline.py config\crawler_config.json data\seed_urls.json data\sample_products.json ...` 无输出。

本阶段未触碰以下禁止文件：

1. `app.py`
2. `src/crawler/fetcher.py`
3. `src/crawler/parser.py`
4. `src/crawler/pipeline.py`
5. `config/crawler_config.json`
6. `data/seed_urls.json`
7. `data/sample_products.json`
8. 阶段1到13.2B归档总结文件

`git status` 中仍有阶段13相关既有未跟踪或修改文件，例如 `FLOW.md`、`PROJECT_CONTROL.md`、`PROJECT_ROADMAP_AND_COACHING.md`、`STAGE13_PLAN.md`、`STAGE13_SUMMARY.md`、`STAGE13_2B_PLAN.md`、`STAGE13_2B_SUMMARY.md`、`data/stage13_sample_products.json`、`data/stage13_seed_urls.json`、`tests/test_stage13_real_sample_acceptance.py` 等。它们是当前工作区既有状态或前序阶段产物，不属于阶段14新增目标。

## 残余风险

1. V2-A 仍依赖客户人工确认候选商品，不能自动证明平台价格、库存、规格和服务实时有效。
2. 候选链接清单只解析客户粘贴的文本，不读取平台详情页；纯链接无法自动得到真实标题、价格、图片或规格。
3. 页面未做真实浏览器手工演示验收，建议交付前用 `streamlit run ui_streamlit.py` 走一次上传 Word、上传 TXT 链接清单、下载 Word 的完整流程。
4. 真正更自动的数据接入需要后续 V2-B 的授权 API、合规第三方商品数据或客户导出数据支持。

## 下一阶段建议

阶段15 建议进入 V2-A+ 智能寻源助手：

1. 生成精准词、放宽词、替代词和排除词。
2. 输出淘宝/京东筛选建议，如价格区间、企业店、发票、配送安装、售后要求。
3. 支持从混合文本中更智能地识别商品候选信息。
4. 增加人工确认向导。
5. 增强推荐解释、排除原因和风险等级。
6. 增加 Excel/CSV 评分表下载。

## 最终结论

可以进入阶段15：V2-A+ 智能寻源助手。
