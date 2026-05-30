# 阶段14执行计划：V2-A 浏览器辅助式淘宝/京东寻源 MVP

## 目标

把阶段13.2B 的上传推荐闭环升级为 V2-A：客户在自己的浏览器中正常登录淘宝/京东并人工确认候选商品，系统负责生成寻源入口、导入候选商品或链接清单、标准化字段、提示待复核、规则排序、展示 Top 推荐并输出可下载 Word 报告。

## 边界

本阶段不做强抓淘宝/京东搜索页，不保存淘宝/京东账号、密码或 Cookie，不绕验证码和风控，不使用代理池，不自动下单，不抓个人信息，不承诺最终采购结论。

候选链接清单只代表客户主动提供的数据。系统只解析清单中的链接和同一行客户填写的标题、价格、尺寸、材质、安装服务等文本，不访问淘宝/京东页面，不编造商品字段。

## 功能项

1. 采购 Word 上传或固定路径读取。
2. 根据采购指标生成淘宝/京东搜索词和搜索链接。
3. 页面提示客户在自己的浏览器中正常登录并人工确认候选商品。
4. 支持候选商品 JSON 导入。
5. 支持候选商品 CSV 导入。
6. 支持候选链接清单 TXT 导入。
7. 将候选链接清单标准化成候选商品记录。
8. 缺失字段标记为待人工复核。
9. 复用现有规则排序和 Top 推荐。
10. Streamlit 页面展示 Top 推荐商品。
11. 输出并下载 Word 报告。
12. 下载候选商品 JSON 和排序结果 JSON。

## 文件范围

允许新增：

1. `STAGE14_V2A_PLAN.md`
2. `STAGE14_V2A_SUMMARY.md`
3. `tests/test_stage14_v2a_sourcing_flow.py`
4. `data/stage14_candidate_links_demo.txt`
5. `data/stage14_candidate_products_demo.csv`

允许小改：

1. `TASKS.md`
2. `ui_streamlit.py`
3. `main.py`
4. `src/product_loader.py`
5. `src/product_ranker.py`
6. `src/doc_writer.py`

禁止修改：

1. `app.py`
2. `src/crawler/fetcher.py`
3. `src/crawler/parser.py`
4. `src/crawler/pipeline.py`
5. `config/crawler_config.json`
6. `data/seed_urls.json`
7. `data/sample_products.json`
8. 阶段1到13.2B归档总结文件

## 验收标准

1. 客户上传 Word 后能获得淘宝/京东搜索词和搜索链接。
2. 客户可导入候选商品 CSV/JSON。
3. 客户可导入候选链接清单 TXT。
4. 链接清单可标准化为候选商品记录，且纯链接缺失字段会提示待人工复核。
5. 系统可排序并展示 Top 推荐。
6. 系统可生成并下载 Word 报告。
7. 固定路径 `python main.py` 不受影响。
8. 阶段13.2B 和旧阶段测试继续通过。
9. 不出现强抓、Cookie、代理池、验证码绕过或最终采购结论正向表述。
