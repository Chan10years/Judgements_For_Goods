# 采购商品推荐与 Word 自动填充系统流程文档

## 1. 项目真实目标

客户真实目标是“采购 Word 到商品推荐 Word”的闭环。最终理想能力包含淘宝、京东等平台的自动寻源，但当前可交付版本是 V1 半自动采购推荐与 Word 交付系统。

```text
采购 Word
→ 采购指标解析
→ 寻源辅助或候选商品导入
→ 商品字段标准化
→ 人工复核
→ 规则排序
→ Top 推荐
→ Word 报告输出
```

## 2. 当前已完成能力

已完成能力包括：

1. Word 技术参数表解析。
2. 候选商品 JSON 读取和字段标准化。
3. 客户候选商品 JSON/CSV 导入适配。
4. 公开 URL 采集底座、失败记录、日志和报告。
5. 人工复核清单、复核模板、复核校验和复核回填。
6. 规则排序、Top 推荐、匹配理由和风险提示。
7. Word 参数响应写回、Top 推荐汇总和交付报告摘要。
8. Streamlit 操作界面。
9. 阶段 13.1 真实公开 URL 和半真实样例验收。

当前流程不能描述为淘宝/京东全自动搜索。淘宝/京东搜索结果自动抓取、商品详情解析和图片证据处理属于 V2。

## 3. V1 交付版数据流

V1 数据流如下：

```text
input.docx
→ requirements.json
→ taobao_jd_search_keywords / search_links（寻源辅助）
→ uploaded_candidates.json 或 uploaded_candidates.csv
→ crawler_products.json
→ manual_review_items.json
→ manual_review_filled_template.json
→ manual_review_validation_report.json
→ reviewed_products.json
→ ranked_products.json
→ responses.json
→ recommendation_result.docx
```

说明：

1. `input.docx` 是客户上传或系统读取的采购 Word。
2. `requirements.json` 是解析后的采购指标。
3. 搜索关键词和搜索入口用于辅助采购员在淘宝/京东寻源，不代表自动抓取。
4. 候选商品 JSON/CSV 由采购员确认、导入或由合规数据源提供。
5. 系统对候选商品做标准化、复核、排序和 Word 输出。

## 4. V1 主流程

### 4.1 Word 输入与指标解析

输入：

```text
采购技术规范 Word
```

处理：

1. 定位技术参数表。
2. 解析序号、技术参数名称、单位、项目需求值或表述、投标人响应值。
3. 输出结构化采购指标。

输出：

```text
requirements.json
```

### 4.2 淘宝/京东寻源辅助

输入：

```text
requirements.json
```

处理：

1. 根据采购指标生成搜索关键词。
2. 生成淘宝、京东搜索入口。
3. 供采购员打开平台页面并确认候选商品。

输出：

```text
搜索关键词
淘宝搜索链接
京东搜索链接
```

限制：

```text
V1 不自动抓取淘宝/京东搜索结果。
V1 不绕登录、验证码、风控。
```

### 4.3 候选商品导入

输入：

```text
候选商品 JSON
候选商品 CSV
客户授权数据源产物
```

字段建议：

```text
title
platform
price
shop
url
image_url
specs_text
service_text
raw_text
source
evidence_text
```

处理：

1. 读取客户确认的候选商品。
2. 统一字段命名。
3. 标准化价格、标题、来源、规格、服务、图片链接和证据文本。
4. 标记字段缺失和证据不足项。

输出：

```text
crawler_products.json
manual_review_items.json
```

### 4.4 人工复核

处理：

1. 根据缺失字段生成复核清单。
2. 生成客户可填写复核模板。
3. 校验客户填写后的复核文件。
4. 只回填人工明确确认且非空的字段。
5. approved 商品优先进入推荐流程。

输出：

```text
manual_review_filled_template.json
manual_review_validation_report.json
reviewed_products.json
review_report.json
```

### 4.5 规则排序与 Top 推荐

处理：

1. 根据采购指标和候选商品字段计算匹配分。
2. 生成匹配理由。
3. 生成风险提示。
4. 排除明显无关或低置信度候选。
5. 选择 Top 推荐商品。

输出：

```text
ranked_products.json
```

排序结果必须表述为采购辅助候选，不能称为最终采购结论。

### 4.6 Word 报告输出

处理：

1. 将参数响应写回 Word。
2. 附加 Top 推荐商品表。
3. 附加数据来源说明。
4. 附加人工复核状态说明。
5. 附加字段风险提示。
6. 附加输出文件索引。

输出：

```text
recommendation_result.docx
```

## 5. V2 自动寻源流程

V2 自动寻源范围：

```text
requirements.json
→ 自动搜索淘宝/京东或合规商品数据源
→ 自动抓取或读取商品详情
→ 自动提取标题、价格、店铺、链接、图片链接、规格、服务说明、证据文本
→ 自动形成候选商品池
→ 接入 V1 复核、排序和 Word 输出流程
```

V2 前提条件：

1. 平台授权接口。
2. 合规第三方商品搜索 API。
3. 客户导出的商品数据。
4. 可稳定访问的公开商品页面。
5. 明确的数据合规边界。

V2 不得通过绕过登录、验证码、风控、偷 Cookie 或代理池来实现。

## 6. 最后一天执行计划

阶段 13.2B 优先完成：

1. 上传采购 Word。
2. 上传候选商品 JSON/CSV。
3. 下载推荐 Word。
4. 淘宝/京东搜索关键词和搜索入口辅助。
5. 交付说明文档。

不在最后一天做：

1. 全自动淘宝/京东抓取。
2. 商品图片证据处理闭环。
3. 登录态、验证码或风控处理。
4. 代理池。
5. 自动下单。

## 7. 不做事项

V1 不做：

1. 不做全自动淘宝/京东抓取。
2. 不绕登录、验证码、风控。
3. 不偷 Cookie。
4. 不使用代理池。
5. 不自动下单。
6. 不抓取个人信息。
7. 不承诺最终采购结论。

## 8. 阶段路线重排

```text
阶段13.2A：全局交付路线重写与客户目标校准
阶段13.2B：应急交付 MVP，Word 上传与候选商品导入闭环
阶段14：错误处理和可维护性
阶段15：交付包整理
阶段16：最终验收文档
V2：淘宝京东自动寻源与图片证据处理
```

## 9. 客户交付话术

```text
当前版本支持半自动采购推荐闭环。系统解析采购 Word 后，可以辅助生成淘宝/京东寻源关键词和搜索入口；采购员确认或导入候选商品后，系统自动完成字段整理、人工复核、规则排序、Top 推荐和 Word 报告输出。

淘宝/京东全自动搜索、商品详情抓取和图片证据处理属于后续 V2，需要合规数据源或授权接口。
```
