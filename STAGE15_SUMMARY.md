# 阶段15总结：V2-A+ 智能寻源助手

## 修改文件列表

新增：

1. `STAGE15_PLAN.md`
2. `STAGE15_SUMMARY.md`
3. `src/sourcing_assistant.py`
4. `tests/test_stage15_smart_sourcing_assistant.py`
5. `data/stage15_candidate_mixed_text_demo.txt`
6. `data/stage15_sourcing_keywords_demo.json`

小改：

1. `main.py`
2. `ui_streamlit.py`
3. `src/doc_writer.py`
4. `TASKS.md`

## V2-A+ 功能说明

阶段15在阶段14浏览器辅助式上传闭环上增加智能寻源辅助能力：生成搜索词和搜索链接，给出平台筛选建议，解析客户主动上传或粘贴的候选链接/混合文本，生成待复核字段、人工确认问题、推荐解释，并导出 Word 与 CSV 评分表。

## 智能搜索词说明

`src/sourcing_assistant.py` 新增 `generate_sourcing_keywords()`，根据采购指标生成精准词、放宽词、替代词和排除词，并保留淘宝/京东搜索链接字段。示例会识别 `1600x750x750`、钢制/颗粒板、配送安装等关键词。

## 平台筛选建议说明

新增 `generate_platform_filter_suggestions()`，输出价格区间、店铺类型、发票、配送安装、本地/同城/批量采购、规格完整性、售后、截图或页面证据等采购辅助建议。建议不写成采购结论。

## 混合文本导入说明

新增 `parse_candidate_mixed_text()` 和 `load_candidate_mixed_text_file()`。TXT 导入支持客户粘贴的链接与同一行可见文本，尽量识别平台、链接、商品名、价格、尺寸、材质、颜色、安装服务和证据文本。纯链接只保留链接和平台线索，标题、价格、尺寸、材质等字段标记待人工复核。

## 人工确认向导说明

新增 `build_manual_confirmation_questions()`，为候选商品生成价格口径、尺寸、材质、配送安装、店铺/链接/截图证据、图片或页面截图、继续补充字段等确认问题。

## 推荐解释增强说明

新增 `enrich_ranked_products_with_sourcing_guidance()`，在不改写 `product_ranker` 核心算法的前提下，给排序结果追加命中指标、待复核字段、主要风险、排名较低原因、明显不适合商品排除原因、推荐等级和结构化解释。

## CSV/Excel 评分表说明

已实现 CSV 评分表输出：`write_scoring_csv()` 生成 `sourcing_score_table.csv`。字段包含排名、商品名称、平台、价格、尺寸、材质、安装服务、商品链接、图片链接、匹配分数、命中指标、待复核字段、风险提示、人工确认问题和推荐等级。Excel 可在后续阶段按交付需要补充。

## UI 增强说明

`ui_streamlit.py` 将 V2-A 区块升级为 V2-A+ 智能寻源助手，展示智能搜索词、淘宝/京东搜索链接、平台筛选建议、上传 Word、上传 JSON/CSV/TXT、Top 推荐表、人工确认问题，并提供 Word、候选 JSON、排序 JSON、CSV 评分表下载。阶段12旧按钮和阶段14上传闭环仍保留。

## 测试命令与结果

1. `python -m unittest tests.test_stage15_smart_sourcing_assistant`：通过，12 tests。
2. `python -m unittest tests.test_stage14_v2a_sourcing_flow`：通过，7 tests。
3. `python -m unittest discover tests`：通过，83 tests。
4. `python -m py_compile main.py`：通过。
5. `python -m py_compile ui_streamlit.py`：通过。
6. `python -m py_compile src/doc_writer.py`：通过。
7. `python -m py_compile src/sourcing_assistant.py`：通过。
8. `python main.py`：通过，生成 `outputs/recommendation_result.docx`、`outputs/ranked_products.json`、`outputs/responses.json`、`outputs/sourcing_score_table.csv`。
9. `git status`：通过查看。工作树仍包含进入阶段15前已存在的阶段13/14与项目控制文件未提交变更；本阶段新增和小改文件见上方列表。

## 是否触碰禁止文件

未触碰以下禁止或原则上不改文件：`src/crawler/fetcher.py`、`src/crawler/parser.py`、`src/crawler/pipeline.py`、`config/crawler_config.json`、`data/seed_urls.json`、`data/sample_products.json`、阶段1到14归档总结文件。

## 为什么没有越界强抓淘宝/京东

阶段15只解析客户主动上传或粘贴的本地文本和文件，没有对淘宝/京东搜索页或商品页发起请求。代码未调用爬虫抓取链路，未写入账号、密码或 Cookie，未规避登录/验证码/风控，也未引入代理池。淘宝/京东链接仅作为人工浏览入口和可追溯字段。

## 残余风险

1. 混合文本解析依赖正则和关键词，复杂商品描述可能仍需人工补全。
2. 价格、安装服务、发票和库存等信息只来自客户提供文本，仍需人工确认。
3. CSV 已满足本阶段低成本交付，原生 xlsx 评分表可在后续按需要补充。
4. 推荐等级仍基于本地规则包装说明，不能替代采购人员判断。

## 下一阶段建议

阶段16建议集中补强错误处理和可维护性：统一异常提示、输入校验、日志口径、导入失败诊断、UI 错误反馈和核心模块边界说明。

## 最终结论

可以进入阶段16
