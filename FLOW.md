采购商品推荐与 Word 自动填充系统流程文档

## 1. 本文档作用

本文档用于规定客户交付版系统的数据流、主流程和验收节点。

系统开发过程中，所有功能都必须服务这条主线：

```text
Word 输入
→ 需求解析
→ 数据源选择
→ 商品采集或导入
→ 商品标准化与去重
→ 规则评分排序
→ Top 3 候选
→ 参数响应生成
→ Word 写回
→ 采集报告与风险报告
→ 客户验收输出
```

项目当前阶段为阶段 8 准备阶段。阶段 1-7 的 Word 读取写回、本地商品数据、规则评分排序、Top 3 推荐和 `main.py` 端到端流程已经完成。阶段 8 重点是生产级商品数据采集子系统 v1。

## 2. 客户交付数据流

客户交付版数据流如下：

```text
input.docx
↓
requirements.json
↓
seed_urls.json 或 sample_products.json
↓
crawler_raw.json
↓
crawler_products.json
↓
crawler_report.json
↓
ranked_products.json
↓
responses.json
↓
recommendation_result.docx
↓
final_report.json 或 final_report.md，后续阶段可做
↓
crawler_run.log
```

每一步都要能单独检查。这样做的目的：

1. 出问题时能快速定位是哪一步坏了。
2. 每次开发只改一个明确环节。
3. 外部采集失败时，可以切回本地测试或手动导入数据。
4. 客户可以查看输入、输出、失败原因、推荐依据和风险提示。
5. 无法确认的参数必须标记“需人工复核”。

## 3. 数据文件说明

### 3.1 input.docx

采购技术规范 Word 输入文件。

来源可以是客户上传、客户提供样例或项目测试样例。

### 3.2 requirements.json

从 Word 技术参数表解析出的采购需求。

典型字段：

1. `index`
2. `name`
3. `unit`
4. `required_value`
5. `response_value`

### 3.3 seed_urls.json

客户提供的公开 URL 列表，或经配置生成的初始 URL 列表。

该文件服务于采集流程，必须可追踪、可去重、可验收。

### 3.4 sample_products.json

本地测试或兜底商品数据。

当外部采集失败、客户未提供授权数据源、目标站点受限或阶段验收不需要联网时，系统应能使用 `sample_products.json` 继续完成标准化、排序、响应生成和 Word 写回流程。

### 3.5 crawler_raw.json

页面抓取或客户授权数据源读取后的原始结果。

应尽量保留来源 URL、HTTP 状态、抓取时间、原始文本摘要、解析入口和错误信息，便于后续审计。

### 3.6 crawler_products.json

采集并标准化后的商品数据。

它是生产级采集模块向后续评分与推荐模块交付的标准商品列表。

标准字段包括：

1. `platform`
2. `title`
3. `price`
4. `shop`
5. `url`
6. `image_url`
7. `specs_text`
8. `service_text`
9. `raw_text`
10. `source`
11. `evidence`
12. `manual_review_required`

### 3.7 crawler_report.json

采集报告文件。

必须记录：

1. 采集成功。
2. 采集失败。
3. 跳过。
4. robots 限制。
5. HTTP 错误。
6. 解析失败。
7. 字段缺失。
8. 去重结果。
9. 需人工复核项。

该文件用于客户验收、问题追踪和风险说明。

### 3.8 ranked_products.json

规则评分排序结果。

`ranked_products.json` 继续服务排序和推荐，必须包含商品分数、排序理由和风险提示。排序结果是采购辅助候选，不是最终采购结论。

### 3.9 responses.json

写回 Word 的参数响应。

`responses.json` 继续服务 Word 写回。每一条采购参数都应有响应内容，无法确认的参数必须写“需人工复核”。

### 3.10 recommendation_result.docx

客户可查看的输出文档。

文档应包含：

1. 原技术参数表。
2. 填充后的投标人响应值。
3. Top 3 候选商品汇总。
4. 推荐依据。
5. 风险提示。
6. 人工复核提示。

### 3.11 final_report.json 或 final_report.md

后续阶段可做的最终交付报告。

内容可包括采集摘要、数据源摘要、推荐摘要、证据摘要、风险摘要和人工复核清单。

### 3.12 crawler_run.log

采集运行日志。

应记录配置加载、seed URL 读取、robots 检查、请求状态、解析状态、标准化状态、去重状态、输出路径和失败原因。

## 4. 流程 1：Word 输入与需求解析

输入：

```text
input.docx
```

处理内容：

系统读取采购技术规范 Word 中的技术参数表，提取采购参数。

需要读取的字段：

1. 序号。
2. 技术参数名称。
3. 单位。
4. 项目需求值或表述。
5. 投标人响应值。

输出：

```text
requirements.json
```

验收标准：

1. 能读取客户 Word 或样例 Word。
2. 能找到技术参数表。
3. 能提取参数名称和需求值。
4. 缺失字段有明确提示。
5. `requirements.json` 可被后续流程读取。

## 5. 流程 2：数据源配置流程

输入：

```text
采集配置
客户公开 URL 列表
客户授权数据源说明
sample_products.json
```

处理内容：

系统根据配置选择数据来源：

1. 本地测试商品 JSON。
2. 手动导入商品数据。
3. 客户提供的公开 URL 列表。
4. 客户授权数据源。
5. 后续可扩展的平台适配器。

输出：

```text
数据源选择结果
seed_urls.json 或 sample_products.json
```

验收标准：

1. 数据源配置可查看。
2. 数据源类型可切换。
3. 本地 JSON 和手动导入可作为兜底。
4. 未授权或受限数据源不会被强行采集。
5. 配置错误有明确失败原因。

## 6. 流程 3：seed URL 读取流程

输入：

```text
客户提供的公开 URL 列表
采集配置
```

处理内容：

系统读取、校验、去重 seed URL，并记录来源。

输出：

```text
seed_urls.json
```

验收标准：

1. URL 格式校验清楚。
2. 重复 URL 可去重。
3. 无效 URL 进入报告。
4. 每个 URL 保留来源说明。
5. 输出可追踪、可复现。

## 7. 流程 4：robots 检查流程

输入：

```text
seed_urls.json
```

处理内容：

系统在请求页面前检查目标站点 robots 规则和允许范围。

输出：

```text
crawler_report.json
crawler_run.log
```

验收标准：

1. robots 允许的 URL 才进入抓取流程。
2. robots 限制的 URL 被跳过。
3. 跳过原因写入报告和日志。
4. 不绕过目标站点访问规则。

## 8. 流程 5：页面抓取流程

输入：

```text
通过 robots 检查的 URL
采集配置
```

处理内容：

fetcher 按配置限速请求页面或客户授权数据源，记录请求状态、响应摘要、错误原因和重试情况。

输出：

```text
crawler_raw.json
crawler_run.log
```

验收标准：

1. 请求超时可配置。
2. 请求频率可配置。
3. HTTP 错误可记录。
4. 请求失败不导致主流程崩溃。
5. 不绕登录、不绕验证码、不绕平台风控。

## 9. 流程 6：商品解析流程

输入：

```text
crawler_raw.json
```

处理内容：

parser 从原始页面或数据源响应中提取商品信息。

目标字段：

1. 商品标题。
2. 价格。
3. 店铺。
4. 商品链接。
5. 图片链接。
6. 参数文本。
7. 服务文本。
8. 原始文本。

输出：

```text
解析后的商品中间结果
crawler_report.json
```

验收标准：

1. 能解析的商品进入后续标准化。
2. 解析失败写入报告。
3. 字段缺失写入风险。
4. 原始来源可追踪。

## 10. 流程 7：商品标准化与去重流程

输入：

```text
解析后的商品中间结果
sample_products.json
手动导入商品数据
```

处理内容：

normalizer 将不同来源的商品整理成统一字段，deduper 根据 URL、标题、店铺和规格摘要进行去重。

输出：

```text
crawler_products.json
crawler_report.json
```

验收标准：

1. 商品字段统一。
2. 缺失字段可被安全处理。
3. 价格尽量转成可比较格式。
4. 去重记录可追踪。
5. `crawler_products.json` 可直接进入评分排序。

## 11. 流程 8：采集报告生成流程

输入：

```text
seed URL 读取结果
robots 检查结果
页面抓取结果
商品解析结果
标准化与去重结果
```

处理内容：

系统生成采集报告和运行日志。

输出：

```text
crawler_report.json
crawler_run.log
```

验收标准：

1. 成功数量清楚。
2. 失败数量清楚。
3. 跳过数量清楚。
4. robots 限制清楚。
5. HTTP 错误清楚。
6. 解析失败清楚。
7. 字段缺失和人工复核项清楚。

## 12. 流程 9：推荐与 Word 写回流程

输入：

```text
requirements.json
crawler_products.json 或 sample_products.json
```

处理内容：

系统对商品进行规则评分排序，选择 Top 3 候选商品，生成参数响应，并写回 Word。

中间输出：

```text
ranked_products.json
responses.json
```

最终输出：

```text
recommendation_result.docx
```

验收标准：

1. 每个商品有 score、reasons、risks。
2. 相关商品排在前面。
3. `responses.json` 每条采购参数都有响应内容。
4. 无法确认的参数写“需人工复核”。
5. `recommendation_result.docx` 可以打开。
6. 文档中推荐依据和风险提示清楚。
7. 不把规则推荐结果称为最终采购结论。

## 13. 流程 10：客户验收流程

输入：

```text
recommendation_result.docx
requirements.json
crawler_products.json
crawler_report.json
ranked_products.json
responses.json
crawler_run.log
```

处理内容：

客户或客户指定验收人员检查端到端流程、配置、日志、报告、Word 输出、推荐依据和风险提示。

验收重点：

1. 端到端流程可运行。
2. 商品数据采集可配置。
3. 采集结果可追踪。
4. 失败有日志和报告。
5. Word 输出可打开。
6. 推荐依据和风险提示清楚。
7. 无法确认的参数标记“需人工复核”。
8. 采集结果和推荐结果没有被称为最终采购结论。

## 14. 安全与合规边界

系统必须遵守：

1. 不绕登录。
2. 不绕验证码。
3. 不绕平台风控。
4. 不偷用 Cookie。
5. 不使用代理池规避封禁。
6. 不抓取个人信息。
7. 不自动下单。
8. 不承诺万能平台采集。
9. 不把采集结果或推荐结果称为最终采购结论。

## 15. 当前开发优先级

当前优先级是阶段 8：生产级商品数据采集子系统 v1。

下一步应创建 `STAGE8_PLAN.md`，先定义配置结构、模块边界、输入输出、报告格式、日志格式、验收命令和安全红线，再进入实现。
