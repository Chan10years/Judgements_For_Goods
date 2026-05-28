# PROJECT_ROADMAP_AND_COACHING.md

# 采购商品推荐与 Word 自动填充系统总路线与协作指南

## 0. 给新对话的说明

请先完整阅读本文档，再继续和用户协作。

用户当前不是单纯想要代码，而是需要一个可以被一步一步带着推进的工程流程。
回答时不要直接跳到大段开发指令。
需要先确认当前阶段，再给出当前阶段的下一小步。

本项目的核心目标是：

```text
做出一个采购商品推荐与 Word 自动填充 MVP。
```

当前最重要的原则是：

```text
先做可演示闭环，再逐步增强真实数据来源。
```

---

## 1. 项目基本信息

项目路径：

```text
D:\CodeLibrary\Judgements_For_Goods
```

当前已有规划文件：

```text
PROJECT_CONTROL.md
FLOW.md
TASKS.md
```

样例 Word：

```text
data/办公屏风01模板样例.docx
```

输出目录：

```text
outputs/
```

推荐新增路线文档：

```text
PROJECT_ROADMAP_AND_COACHING.md
```

每个阶段建议新增：

```text
STAGE1_PLAN.md
STAGE1_SUMMARY.md

STAGE2_PLAN.md
STAGE2_SUMMARY.md

STAGE3_PLAN.md
STAGE3_SUMMARY.md

STAGE4_PLAN.md
STAGE4_SUMMARY.md

STAGE5_PLAN.md
STAGE5_SUMMARY.md
```

---

## 2. 项目一句话解释

这个项目的目标是：

```text
用户上传采购技术规范 Word，系统解析其中的技术参数表，获取候选商品，对商品进行匹配排序，生成响应内容，最后输出填充后的新 Word。
```

系统主线是：

```text
采购 Word
↓
采购参数
↓
候选商品
↓
匹配排序
↓
响应内容
↓
输出 Word
```

重点理解：

```text
这个项目的核心是采购文档自动填充和商品匹配推荐。
淘宝和京东只是商品数据来源之一。
```

不能把项目成败完全押在淘宝、京东实时搜索上。
必须保留缓存 JSON 或手动导入作为兜底。

---

## 3. 为什么要这样拆

用户之前的问题是 vibe coding 容易乱：

```text
想到一个功能就让 AI 写一个功能
做到哪里算哪里
文件越来越多
系统边界越来越模糊
最后不知道哪里完成了、哪里没完成
```

现在采用阶段制流程：

```text
每个阶段只解决一个核心问题
每个阶段开始先 Plan Mode
计划通过后再实现
实现后验收
验收通过后生成阶段总结
再进入下一阶段
```

这样做的目标是：

```text
让 AI 服从项目文档，而不是让 AI 推着用户乱跑。
```

---

## 4. 总体阶段路线

### 阶段 1：Word 输入输出闭环

目标：

```text
上传 Word
解析技术参数表
页面展示解析结果
生成模拟投标人响应值
写回 Word
下载 output.docx
```

阶段 1 只证明：

```text
系统能读 Word，也能写 Word。
```

阶段 1 不做：

```text
商品数据
商品评分
推荐汇总表
淘宝爬虫
京东爬虫
AI 生成
数据库
登录系统
复杂前端
```

完成标准：

```text
页面可以上传样例 Word
能解析出 13 条技术参数
页面能展示解析结果
每条参数都有非空模拟响应
能生成 outputs/output.docx
输出 Word 可以打开
投标人响应值列被填充
```

---

### 阶段 2：商品数据闭环

目标：

```text
系统能读取 products.json
页面能展示候选商品
商品字段结构统一
```

第一版商品数据来源：

```text
本地缓存 products.json
```

不要先做淘宝京东实时爬虫。

阶段 2 需要准备：

```text
5 到 10 条办公屏风相关商品
1 到 2 条无关商品
```

每条商品字段建议：

```text
platform
title
price
shop
url
image_url
specs_text
service_text
raw_text
```

完成标准：

```text
页面能显示商品列表
商品标题、平台、价格、链接、参数文本可见
缺失字段不会导致系统崩溃
商品数据可以传给后续评分模块
```

---

### 阶段 3：匹配排序闭环

目标：

```text
系统能根据采购参数给商品打分排序。
```

评分规则第一版用规则，不训练模型。

建议评分维度：

```text
标题相关度
尺寸匹配度
材质匹配度
服务匹配度
参数完整度
价格合理性
风险项数量
```

完成标准：

```text
每个商品都有 score
每个商品都有 reasons
每个商品有 risks
相关商品排在前面
无关商品排在后面
排序理由能被用户理解
```

---

### 阶段 4：真实推荐结果写回 Word

目标：

```text
把 Top 商品结果和响应内容写回 Word。
```

阶段 4 才开始写真实推荐响应。

输出 Word 应该包含：

```text
填充后的投标人响应值
推荐商品汇总表
商品名称
平台
价格
链接
匹配分数
匹配理由
风险提示
```

重要红线：

```text
无法从商品数据确认的参数，必须写“需人工复核”。
不能让 AI 或规则编造商品参数。
```

完成标准：

```text
output.docx 能打开
投标人响应值列填入真实推荐相关内容
文档末尾有推荐商品汇总表
风险提示清楚
没有编造参数
```

---

### 阶段 5：真实搜索增强

目标：

```text
尝试接入京东或淘宝搜索数据。
```

顺序建议：

```text
先尝试京东
再尝试淘宝
始终保留 products.json 缓存兜底
```

原因：

```text
淘宝和京东可能出现登录、验证码、反爬、页面结构变化。
演示不能因为平台限制中断。
```

完成标准：

```text
至少完成一个平台的搜索尝试
搜索结果能转成 products.json 格式
搜索失败时能切回缓存 JSON
演示流程不中断
```

---

## 5. 当前状态

已完成：

```text
项目路径已建立
PROJECT_CONTROL.md 已建立
FLOW.md 已建立
TASKS.md 已建立
样例 Word 已放入 data 文件夹
阶段 1 Plan Mode 已完成
阶段 1 计划已被评估为可用
```

当前应执行：

```text
保存 STAGE1_PLAN.md
进入阶段 1 实现
阶段 1 完成后生成 STAGE1_SUMMARY.md
```

当前不能做：

```text
不能进入阶段 2
不能做商品数据
不能做淘宝京东
不能接 AI
不能做评分
不能做推荐汇总表
```

---

## 6. 每个阶段的标准工作流

每个阶段都必须按这个流程走：

```text
1. 读取项目文档
2. 开 Plan Mode
3. 输出该阶段计划
4. 用户审计划
5. 保存 STAGEX_PLAN.md
6. 按计划实现
7. 运行验收
8. 修复问题
9. 生成 STAGEX_SUMMARY.md
10. 更新 TASKS.md 当前状态
11. 再进入下一阶段
```

不能跳过 Plan Mode。
不能跳过验收。
不能只靠聊天记录保存上下文。
所有关键上下文都要落到 Markdown 文件里。

---

## 7. 多对话使用规则

推荐方式：

```text
一个阶段使用一个主对话。
```

不要在同一阶段开多个对话并行修改代码。

正确方式：

```text
阶段 1：一个 Codex 对话完成 Word 闭环
阶段 2：新 Codex 对话读取阶段 1 总结后继续
阶段 3：新 Codex 对话读取前面总结后继续
阶段 4：同理
阶段 5：同理
```

新对话开始时，必须先读：

```text
PROJECT_CONTROL.md
FLOW.md
TASKS.md
PROJECT_ROADMAP_AND_COACHING.md
上一个阶段的 STAGE_SUMMARY.md
当前阶段的 STAGE_PLAN.md
```

如果当前阶段还没有 PLAN，就先用 Plan Mode 生成。

---

## 8. 新对话应该如何带用户

新对话不要一次性给用户所有代码和所有开发细节。

应该按下面方式带：

### 第一步：确认当前状态

先问用户当前目录是否有：

```text
PROJECT_CONTROL.md
FLOW.md
TASKS.md
data/办公屏风01模板样例.docx
outputs/
```

如果是阶段 1，还确认是否有：

```text
STAGE1_PLAN.md
```

### 第二步：明确当前阶段

告诉用户：

```text
现在只做阶段 1：Word 输入输出闭环。
目标是让系统读 Word、写 Word、输出 output.docx。
```

### 第三步：给一小步操作

一次只给用户一个明确动作。

比如：

```text
现在先把 STAGE1_PLAN.md 保存到项目根目录。
保存完告诉我。
```

用户完成后，再进入下一步。

### 第四步：每一步都检查结果

用户做完后，要问：

```text
目录里现在有什么文件？
运行有没有报错？
outputs 里有没有生成 output.docx？
页面有没有显示 13 条参数？
```

### 第五步：只在必要时给 Codex 指令

不要让用户随便把大需求丢给 Codex。

每次给 Codex 指令前，必须明确：

```text
当前阶段
当前任务
允许修改的文件
禁止修改的文件
输入
输出
验收标准
```

---

## 9. 阶段 1 具体路线

阶段 1 当前目标：

```text
实现 Word 输入输出闭环。
```

阶段 1 文件：

```text
requirements.txt
app.py
src/__init__.py
src/doc_parser.py
src/mock_response.py
src/doc_writer.py
STAGE1_PLAN.md
STAGE1_SUMMARY.md
```

运行产物：

```text
outputs/input.docx
outputs/requirements.json
outputs/output.docx
```

阶段 1 推荐实现顺序：

```text
1. 创建 requirements.txt
2. 创建 src 目录和 __init__.py
3. 创建 doc_parser.py
4. 先测试能否解析样例 Word
5. 创建 mock_response.py
6. 创建 doc_writer.py
7. 创建 app.py
8. 运行 Streamlit
9. 上传样例 Word
10. 检查 output.docx
11. 修复问题
12. 生成 STAGE1_SUMMARY.md
```

阶段 1 推荐 Codex 指令：

```text
请根据 STAGE1_PLAN.md 开始实现阶段 1。

当前阶段只做 Word 输入输出闭环。

允许创建或修改：

requirements.txt
app.py
src/__init__.py
src/doc_parser.py
src/mock_response.py
src/doc_writer.py

允许生成：

outputs/input.docx
outputs/requirements.json
outputs/output.docx

目标：

1. Streamlit 页面支持上传 docx
2. 解析 data/办公屏风01模板样例.docx 中的技术参数表
3. 页面展示解析出的 13 条技术参数
4. 为每条参数生成模拟响应
5. 将模拟响应写回“投标人响应值”列
6. 输出 outputs/output.docx
7. 页面提供下载按钮

禁止：

淘宝爬虫
京东爬虫
AI
商品数据
商品评分
推荐汇总表
数据库
登录系统
复杂前端
修改 PROJECT_CONTROL.md
修改 FLOW.md
修改 TASKS.md
修改 STAGE1_PLAN.md

完成后请生成 STAGE1_SUMMARY.md，说明：

1. 创建或修改了哪些文件
2. 如何运行
3. 如何验收
4. 阶段 1 是否达标
5. 还有哪些遗留风险
```

阶段 1 验收方式：

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

上传：

```text
data/办公屏风01模板样例.docx
```

检查：

```text
outputs/output.docx
```

阶段 1 必须看到：

```text
页面显示 13 条技术参数
output.docx 可以打开
投标人响应值列不为空
没有出现商品、AI、淘宝、京东、评分、推荐汇总表
```

---

## 10. 阶段 2 具体路线

进入阶段 2 的前提：

```text
STAGE1_SUMMARY.md 存在
阶段 1 验收通过
output.docx 可以正常打开
```

阶段 2 目标：

```text
引入 products.json，让系统能读取和展示候选商品。
```

阶段 2 开始前操作：

```text
开新对话
让 Codex 读取 PROJECT_CONTROL.md、FLOW.md、TASKS.md、PROJECT_ROADMAP_AND_COACHING.md、STAGE1_SUMMARY.md
使用 Plan Mode 生成 STAGE2_PLAN.md
用户审查后再实现
```

阶段 2 禁止：

```text
禁止淘宝京东实时爬虫
禁止 AI 生成
禁止复杂评分
禁止写真实推荐 Word
```

阶段 2 完成后生成：

```text
STAGE2_SUMMARY.md
```

---

## 11. 阶段 3 具体路线

进入阶段 3 的前提：

```text
products.json 可读取
页面能展示候选商品
STAGE2_SUMMARY.md 存在
```

阶段 3 目标：

```text
根据采购参数对商品打分排序。
```

阶段 3 只做规则评分。

阶段 3 不做：

```text
AI 判断
爬虫
真实 Word 推荐写回
```

阶段 3 完成后生成：

```text
STAGE3_SUMMARY.md
```

---

## 12. 阶段 4 具体路线

进入阶段 4 的前提：

```text
商品评分排序已完成
能选出 Top 商品
STAGE3_SUMMARY.md 存在
```

阶段 4 目标：

```text
根据 Top 商品生成响应内容，写回 Word，并追加推荐商品汇总表。
```

阶段 4 重点红线：

```text
不能编造商品参数。
无法确认的参数必须写“需人工复核”。
```

阶段 4 完成后，系统应基本具备演示价值。

阶段 4 完成后生成：

```text
STAGE4_SUMMARY.md
```

---

## 13. 阶段 5 具体路线

进入阶段 5 的前提：

```text
阶段 1 到阶段 4 主流程已经能跑通。
系统即使不接淘宝京东，也能靠 products.json 完成演示。
```

阶段 5 目标：

```text
尝试真实搜索增强。
```

阶段 5 必须保留兜底：

```text
实时搜索失败时，回到 products.json。
```

阶段 5 不允许：

```text
绕过验证码
高频请求
把账号、cookie、API key 写进代码
把密钥提交到 GitHub
```

阶段 5 完成后生成：

```text
STAGE5_SUMMARY.md
```

---

## 14. 出问题时怎么处理

如果 Codex 跑偏：

```text
立刻停止当前实现。
让它回到当前阶段文档。
重新声明允许修改文件和禁止事项。
```

如果代码报错：

```text
不要直接让 Codex 大改。
先复制报错信息。
确认是哪个阶段、哪个模块、哪个输入输出坏了。
只让 Codex 修复该模块。
```

如果 output.docx 打不开：

```text
优先检查 doc_writer.py。
不要同时修改 parser、writer、app。
```

如果解析不到 13 条参数：

```text
优先检查 doc_parser.py。
确认表头识别逻辑。
不要动 doc_writer.py。
```

如果页面打不开：

```text
优先检查 app.py 和依赖安装。
不要改解析逻辑。
```

---

## 15. 新对话的回答风格要求

新对话应该像项目教练一样带用户：

```text
少讲大道理
每次只推进一个小动作
先解释为什么做这一步
再给具体操作
做完后要求用户反馈结果
根据结果决定下一步
```

不要一次性让用户处理太多事。

推荐节奏：

```text
现在先做第 1 步。
做完把结果发我。
我检查后再给第 2 步。
```

---

## 16. 最终交付目标

周天前理想交付包：

```text
项目源码
requirements.txt
README.md
PROJECT_CONTROL.md
FLOW.md
TASKS.md
PROJECT_ROADMAP_AND_COACHING.md
STAGE_PLAN 和 STAGE_SUMMARY 文件
样例输入 Word
样例输出 Word
products.json
演示截图
简短演示视频
```

最低保命交付：

```text
能运行的本地页面
能上传样例 Word
能解析采购参数
能加载候选商品数据
能排序
能生成新 Word
有样例输入和样例输出
能解释风险和兜底方案
```

---

## 17. 当前下一步

当前马上应该做：

```text
1. 保存本文件为 PROJECT_ROADMAP_AND_COACHING.md
2. 保存阶段 1 计划为 STAGE1_PLAN.md
3. 在 Codex 中根据 STAGE1_PLAN.md 实现阶段 1
4. 运行并验收阶段 1
5. 阶段 1 通过后生成 STAGE1_SUMMARY.md
```

当前不要做：

```text
不要进入阶段 2
不要创建 products.json
不要做商品评分
不要做淘宝京东
不要接 AI
```

---

## 18. 最后总控判断

任何时候都用这三个问题判断下一步：

```text
1. 当前处于哪个阶段？
2. 这一步是否服务当前阶段验收？
3. 做完后有什么明确产物？
```

如果答不上来，就不要做。

当前答案是：

```text
当前处于阶段 1。
这一步服务 Word 输入输出闭环。
做完后产物是 outputs/output.docx 和 STAGE1_SUMMARY.md。
```
