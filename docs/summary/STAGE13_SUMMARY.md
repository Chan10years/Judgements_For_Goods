# 阶段13：真实样例数据验收总结

## 1. 修改文件列表

本阶段新增或更新：

```text
STAGE13_PLAN.md
STAGE13_SUMMARY.md
tests/test_stage13_real_sample_acceptance.py
data/stage13_sample_products.json
data/stage13_seed_urls.json
outputs/stage13_acceptance_report.json
TASKS.md
```

未修改以下禁止源码或配置文件：

```text
app.py
config/crawler_config.json
data/seed_urls.json
data/sample_products.json
main.py
src/doc_writer.py
src/product_loader.py
src/product_ranker.py
src/response_builder.py
src/crawler/*
ui_streamlit.py
```

## 2. 使用的样例

公开 URL 样例文件：`data/stage13_seed_urls.json`

包含 3 个公开 URL：

1. `https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops`
2. `https://example.com/`
3. `https://example.com/stage13-missing-product-page`

半真实商品样例文件：`data/stage13_sample_products.json`

包含 5 个商品：

1. 字段较完整的办公屏风工位候选。
2. 缺少价格、材质、安装服务的办公屏风候选。
3. 证据文本不足的办公屏风候选。
4. 缺少明确来源和链接的办公屏风候选。
5. 明显无关的家用电热水壶候选。

所有半真实样例均只用于阶段13验收，不代表真实报价、库存、安装服务、来源证据或最终采购结论。

## 3. 实际跑通的流程

阶段13专用验收测试 `tests/test_stage13_real_sample_acceptance.py` 已跑通：

1. 阶段13 JSON 样例读取和格式校验。
2. 阶段13 seed URL 文件校验，3 条 URL 均为合法 seed。
3. 公开 URL 采集流程执行完成并生成报告。
4. 半真实 JSON 商品经 `ManualJsonAdapter` 标准化为候选商品。
5. 人工复核清单生成。
6. 客户复核填写模板生成。
7. 故意错误的复核填写文件被校验器识别，产生 1 个 error。
8. 有效复核填写文件通过校验，error 为 0。
9. 复核回填成功，生成 1 个 approved 已复核商品，3 个 needs_more_info 项。
10. 主推荐流程使用已复核商品生成排序、响应和 Word。
11. Word 中保留交付报告摘要、数据来源说明、人工复核状态说明、字段风险提示、输出文件索引和非最终采购结论说明。
12. Streamlit UI 通过伪 `st` 对象半自动验证 5 个按钮均能触发现有 action 函数。

结构化验收报告已输出到：

```text
outputs/stage13_acceptance_report.json
```

## 4. 字段解析、缺失和人工复核

半真实样例成功读取字段：

```text
title
category
price
material
color
dimensions
source
url
specs_text
service_text
raw_text
```

进入人工复核的字段：

```text
dimensions
evidence_text
installation_service
price
source
```

人工复核清单数量：4 项。

客户复核模板数量：4 项。

有效复核回填结果：

```text
approved_count: 1
needs_more_info_count: 3
reviewed_products_count: 1
```

## 5. 真实 URL 采集结果

阶段13公开 URL 采集流程已执行，但当前环境中的外网请求全部失败：

```text
total_url_count: 3
valid_url_count: 3
success_count: 0
failure_count: 3
skipped_count: 0
主要失败原因: network_error
```

失败原因均为代理/网络连接被拒绝，请求被转到 `127.0.0.1:9` 后无法连接。

这说明现有采集流程能清楚记录失败 URL 和失败原因，但本次环境没有取得成功的真实 URL 商品解析结果。

## 6. Word 和 UI 验收

Word 已成功生成。

阶段13专用 Word 输出路径：

```text
outputs/stage13_test_workspace/runtime/recommendation/recommendation_result.docx
```

默认主流程 Word 输出路径：

```text
outputs/recommendation_result.docx
```

Word 交付报告增强内容仍存在：

```text
交付报告摘要: 存在
数据来源说明: 存在
人工复核状态说明: 存在
字段风险提示: 存在
输出文件索引: 存在
不代表最终采购结论: 存在
```

UI 半自动验收通过，验证的 action：

```text
run_crawler_action
run_main_pipeline_action
generate_review_template_action
validate_review_filled_action
apply_review_action
```

## 7. 测试命令与结果

已执行必需命令：

```text
python -m unittest discover tests
结果：通过，53 tests OK

python -m py_compile main.py
结果：通过

python -m py_compile src/doc_writer.py
结果：通过

python -m py_compile ui_streamlit.py
结果：通过

python -m src.product_fetcher
结果：通过，默认 data/seed_urls.json 为空，采集 0 个 URL

python -m src.crawler.review
结果：通过，默认人工复核项 0

python -m src.crawler.review_apply
结果：通过，默认复核模板 0 项，已复核商品 0

python main.py
结果：通过，回退使用 data/sample_products.json，生成 outputs/recommendation_result.docx

python -m json.tool outputs/ranked_products.json
结果：通过

python -m json.tool outputs/responses.json
结果：通过

git status
结果：未发现阶段13禁止源码文件变更；仍存在用户既有未跟踪文件 STAGE9_12_GIT_AUDIT_SUMMARY.md
```

额外执行：

```text
python -m json.tool data/stage13_seed_urls.json
结果：通过

python -m json.tool data/stage13_sample_products.json
结果：通过

python -m json.tool outputs/stage13_acceptance_report.json
结果：通过
```

## 8. 是否触碰禁止文件

未触碰阶段13禁止修改的源码、默认配置和默认样例文件。

`git diff --name-only` 仅显示允许小改的 `TASKS.md`。

`git status --short` 显示允许小改的 `TASKS.md`、阶段13新增文件，以及用户既有未跟踪文件 `STAGE9_12_GIT_AUDIT_SUMMARY.md`。

## 9. 残余风险

1. 当前环境外网请求全部失败，无法证明公开 URL 商品页面能成功解析。
2. 半真实样例链路已通过，但不能替代真实商品页字段解析验收。
3. 公开 URL 失败没有进入字段缺失人工复核，因为请求阶段已经失败，尚未产生可解析商品。
4. 本阶段按要求没有修复源码问题，只记录验收暴露的问题。

## 10. 阶段13验收结论

半真实样例数据的采集后续链路、复核、推荐、Word 和 UI 半自动触发均通过。

真实公开 URL 样例在当前环境下全部因网络代理连接失败，未取得真实商品解析成功样例。

该结论已在阶段13.1通过临时清除错误代理并重跑真实 URL 验收后更新，详见第12节。

阶段13原始结论：

```text
需要补充真实样例后再验收
```

## 11. 下一阶段建议

先补充可访问的公开商品样例，或在可联网环境重新执行阶段13公开 URL 采集验收。

如果真实 URL 采集仍受环境限制，可明确采用客户提供的半真实 JSON/CSV 作为验收输入，但需要在交付记录中继续标注“非最终采购结论、需人工复核”。

## 12. 阶段13.1：代理环境修正后重跑真实 URL 验收

执行日期：2026-05-31。

阶段13.1只修正当前命令会话代理环境并重跑真实公开 URL 验收，未修改业务源码、爬虫核心逻辑、推荐算法、平台适配器或默认 seed 文件。

### 12.1 修正前代理变量

CMD 检查结果：

```text
HTTP_PROXY=http://127.0.0.1:9
HTTPS_PROXY=http://127.0.0.1:9
ALL_PROXY=http://127.0.0.1:9
GIT_HTTP_PROXY=http://127.0.0.1:9
GIT_HTTPS_PROXY=http://127.0.0.1:9
NO_PROXY=localhost,127.0.0.1,::1
```

说明：用户要求清除的 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY` 及小写变量清除后，Python 仍识别到 `GIT_HTTP_PROXY` 和 `GIT_HTTPS_PROXY`，因此阶段13.1在当前命令会话里也一并临时清除了这两个 Git 代理变量。

### 12.2 修正后 Python 代理识别

临时清除代理变量后：

```text
python -c "import requests; print(requests.utils.get_environ_proxies('https://example.com'))"
```

输出：

```text
{'no': 'localhost,127.0.0.1,::1'}
```

不再出现 `127.0.0.1:9`。

### 12.3 基础联网测试

命令：

```text
python -c "import requests; r=requests.get('https://example.com', timeout=10); print(r.status_code, r.url)"
```

结果：

```text
200 https://example.com/
```

### 12.4 阶段13真实 URL 重跑结果

阶段13专用验收测试读取 `data/stage13_seed_urls.json` 重跑成功：

```text
python -m unittest tests.test_stage13_real_sample_acceptance
结果：通过，1 test OK
```

公开 URL 采集重跑结果：

```text
total_url_count: 3
valid_url_count: 3
success_count: 1
failure_count: 1
skipped_count: 1
manual_review_items_count: 1
```

每个 URL 状态：

1. `https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops`
   - 状态：跳过。
   - 原因：`robots_disallowed`。
   - robots：`https://webscraper.io/robots.txt`。
2. `https://example.com/`
   - 状态：采集成功，但字段缺失，进入人工复核。
   - 成功解析字段：`platform`、`title`、`url`、`raw_text`、`source`、`notes`、`evidence`、`evidence_text`、`h1`。
   - 标题：`Example Domain`。
   - 缺失字段：`price`、`specs_text`、`service_text`、`dimensions`、`material`、`installation_service`。
3. `https://example.com/stage13-missing-product-page`
   - 状态：失败。
   - 原因：`HTTP 404`。

### 12.5 Word、测试和 JSON 校验

已执行并通过：

```text
python -m json.tool data/stage13_seed_urls.json
python -m src.product_fetcher
python -m src.crawler.review
python -m src.crawler.review_apply
python main.py
python -m unittest discover tests
python -m json.tool outputs/crawler_report.json
python -m json.tool outputs/crawler_products.json
python -m json.tool outputs/manual_review_items.json
python -m json.tool outputs/stage13_acceptance_report.json
git status
```

结果摘要：

```text
python -m unittest discover tests: 通过，53 tests OK
python main.py: 通过，Word 成功生成 outputs/recommendation_result.docx
默认 python -m src.product_fetcher: 通过；默认 data/seed_urls.json 仍为空，因此默认采集 0 个 URL
阶段13专用真实 URL 验收: 成功 1 个、失败 1 个、robots 跳过 1 个
```

### 12.6 是否触碰禁止文件

未修改业务源码、爬虫核心逻辑、推荐算法、UI、默认配置、默认 seed 或默认样例商品。

阶段13.1仅更新：

```text
STAGE13_SUMMARY.md
outputs/stage13_acceptance_report.json
TASKS.md
```

### 12.7 阶段13.1最终结论

阶段13.1满足验收判断：至少 1 个真实公开 URL 成功采集，失败 URL 有明确失败原因，字段缺失能进入人工复核；Word 和测试仍通过。

最终结论：

```text
可以进入阶段13.2A
```

### 12.8 残余风险

1. 本次只临时清除当前命令会话代理变量，没有修改系统永久代理配置；新终端仍可能继承 `127.0.0.1:9`。
2. `example.com` 不是商品页，只能验证公开 URL 请求、标题解析、字段缺失和人工复核链路，不能代表真实商品页字段丰富度。
3. WebScraper 测试页被 robots 限制跳过，符合安全红线，但未形成商品解析样例。

## 13. 阶段13.2A：全局交付路线重写与客户目标校准

执行目的：阶段13.1后重新校准客户真实目标和项目交付路线。当前系统已完成 Word 解析、候选商品数据处理、规则排序、Top 推荐、Word 写回、人工复核闭环、Streamlit 操作界面和 Word 交付报告增强，但客户真实目标是“上传采购 Word 后，系统能在淘宝和京东搜索并筛选符合采购指标的商品，形成推荐商品数据，再写回 Word”。

阶段13.2A重新定义交付路线：

```text
V1：半自动采购推荐与 Word 交付系统
V2：淘宝京东自动寻源与采购推荐系统
```

### 13.1 项目真实目标

客户要的是采购 Word 到商品推荐 Word 的闭环。最终理想能力包含淘宝、京东自动寻源、商品详情解析、图片证据处理、候选商品池自动生成、规则排序和 Word 报告输出。

当前可交付版本为 V1 半自动闭环。V1 通过人机协同完成采购推荐：系统解析采购 Word，辅助生成淘宝/京东寻源关键词和搜索入口；采购员确认或导入候选商品后，系统自动完成字段整理、人工复核、规则排序、Top 推荐和 Word 报告输出。

### 13.2 当前已完成能力边界

阶段1到13.1已经完成的能力可以支撑 V1 后半段自动化，但不能被夸大为淘宝/京东全自动搜索系统。

当前系统还没有：

```text
淘宝/京东自动搜索适配器
真实平台商品页解析策略
图片证据处理闭环
自动形成淘宝/京东候选商品池的稳定能力
```

### 13.3 V1 交付范围

V1 支持：

1. 上传或读取采购 Word。
2. 解析采购指标。
3. 导入候选商品 JSON/CSV。
4. 商品字段标准化。
5. 人工复核清单。
6. 复核回填。
7. 规则排序。
8. Top 推荐。
9. Word 报告输出。
10. Streamlit 操作界面。
11. 淘宝/京东搜索关键词和搜索入口辅助。

V1 不承诺全自动抓取淘宝/京东搜索结果，不绕登录、验证码、风控，不偷 Cookie，不使用代理池，不自动下单，不把结果称为最终采购结论。

### 13.4 V2 自动寻源范围

V2 目标能力：

1. 根据 Word 指标自动生成搜索任务。
2. 自动搜索淘宝、京东或合规商品数据源。
3. 自动获取候选商品标题、价格、店铺、链接、图片链接、规格、服务说明和证据文本。
4. 自动形成候选商品池。
5. 自动处理图片链接、图片证据和必要的可追溯证据。
6. 接入 V1 已完成的复核、排序和 Word 输出流程。

V2 前提条件：

```text
平台授权接口
合规第三方商品搜索 API
客户导出的商品数据
可稳定访问的公开商品页面
明确的数据合规边界
```

### 13.5 最后一天执行计划

最后一天优先进入阶段13.2B，应急交付 V1 MVP：

1. 上传采购 Word。
2. 上传候选商品 JSON/CSV。
3. 下载推荐 Word。
4. 淘宝/京东搜索关键词和搜索入口辅助。
5. 交付说明文档。

### 13.6 阶段路线重排

阶段13.2A后路线调整为：

```text
阶段13.2A：全局交付路线重写与客户目标校准
阶段13.2B：应急交付 MVP，Word 上传与候选商品导入闭环
阶段14：错误处理和可维护性
阶段15：交付包整理
阶段16：最终验收文档
V2：淘宝京东自动寻源与图片证据处理
```

### 13.7 客户交付话术

统一客户交付口径：

```text
当前版本支持半自动采购推荐闭环。系统可以解析采购 Word，辅助生成淘宝/京东寻源关键词和搜索入口；采购员确认或导入候选商品后，系统自动完成字段整理、人工复核、规则排序、Top 推荐和 Word 报告输出。

淘宝/京东全自动搜索、商品详情抓取和图片证据处理属于后续 V2，需要合规数据源或授权接口。
```

### 13.8 阶段13.2A结论

阶段13.2A只做全局规划文档和任务总控文档更新，不写新功能，不修改业务源码，不进入阶段14。

阶段13.2A完成后的判断口径：

```text
可以进入阶段13.2B
```
