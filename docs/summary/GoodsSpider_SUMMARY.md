# GFoodsSpider 改造总结

更新时间：2026-06-01

## 1. 改造目标

本次改造的目标是把现有项目调整为“采购商品推荐系统”：

- 用户输入或上传预备采购商品的采购指标数据。
- 系统参考 GoodsSpider 的浏览器自动化思路，在淘宝、京东搜索候选商品。
- 系统解析商品标题、价格、店铺、图片、链接等信息，并结合采购指标进行筛选和排序。
- 系统展示满足条件的推荐商品。
- 系统生成结构化结果，支持下载使用；高级流程中可把推荐结果写回 Word 文档。

参考项目：

- https://github.com/Srpihot/GoodsSpider

## 2. 已完成能力

### GoodsSpider 风格搜索

新增 `src/marketplace_spider.py`，实现基于 Selenium 的淘宝、京东搜索能力：

- 支持 Edge/Chrome 浏览器驱动。
- 支持淘宝搜索结果解析。
- 支持京东搜索结果解析。
- 支持识别淘宝登录、验证码、风控拦截页面。
- 支持识别京东登录页面。
- 支持 Headless 和人工登录浏览器模式。
- 将 Selenium 运行缓存固定到 `outputs/selenium_runtime/cache`，避免污染系统目录。

### 淘宝结果适配

新增 `src/crawler/adapters/taobao_search_adapter.py`：

- 支持解析淘宝搜索 HTML 或 JSON 导出文件。
- 支持提取标题、价格、店铺、销量、图片、链接等字段。
- 可作为线上抓取失败时的备用导入方式。

### 采购指标解析与排序

在 `src/sourcing_assistant.py` 和 `main.py` 中补充采购指标处理能力：

- 从用户输入或 Word 文档中抽取采购关键词、预算、规格、指标要求。
- 对候选商品进行规则化打分。
- 优先推荐价格、标题关键词、店铺、销量等信息更匹配的商品。
- 生成 JSON、CSV、DOCX 等结果文件。

### Streamlit 页面改造

`ui_streamlit.py` 已调整为面向客户的采购推荐流程：

- 首页聚焦“采购商品推荐系统”，不再要求用户理解底层阶段按钮。
- 用户主要操作是输入采购指标、采购关键词，选择淘宝/京东搜索。
- 页面展示推荐商品、商品来源、价格、链接、排序分数和下载入口。
- 原有阶段工具移入“高级工具”区域，避免主流程混乱。

## 3. 输出文件

主要结果文件：

- `docs/GFoodsSpider_SUMMARY.md`：本总结文档。
- `docs/采购商品推荐系统改造总结与验收报告.docx`：正式 Word 总结报告。
- `outputs/taobao_procurement_recommendations/`：采购推荐结构化输出目录。
- `outputs/marketplace_doc_recommendations/`：Word 文档推荐流程输出目录。

主要代码文件：

- `main.py`
- `ui_streamlit.py`
- `src/marketplace_spider.py`
- `src/crawler/adapters/taobao_search_adapter.py`
- `src/sourcing_assistant.py`
- `tests/test_stage16_taobao_procurement_recommendation.py`

## 4. 验收结果

已完成的本地验收：

- `python -m unittest discover -s tests -p test*.py`：94 个测试通过。
- `python -m py_compile main.py ui_streamlit.py src\marketplace_spider.py src\crawler\adapters\taobao_search_adapter.py src\sourcing_assistant.py`：编译检查通过。
- Streamlit 页面访问 `http://127.0.0.1:8501/` 返回正常。
- 淘宝真实搜索会遇到登录、验证码或风控拦截时，系统可以识别并提示使用人工登录浏览器模式。
- 京东真实搜索遇到登录页时，系统可以识别为登录要求，而不是误判为无结果。

## 5. 当前限制

淘宝、京东都存在反爬、登录、验证码、风控策略。当前实现严格参考 GoodsSpider 的浏览器自动化路线，但不会绕过平台安全机制：

- 未保存淘宝、京东账号密码。
- 未保存用户 Cookie。
- 未注入恶意脚本。
- 未修改系统浏览器配置。
- 未绕过验证码或平台风控。

因此，真实线上搜索可能需要人工登录或改接合规数据源/API。生产环境如果要稳定使用，建议优先接入企业采购平台、开放接口、授权数据源或客户允许的数据导出文件。

## 6. 后续建议

下一阶段建议按以下顺序继续：

1. 固定客户 Word 模板字段，明确 AI 回填位置和表格格式。
2. 增加人工登录浏览器模式的页面提示和操作说明。
3. 为淘宝、京东分别增加更稳定的字段解析兜底规则。
4. 增加图片匹配能力，例如按主图识别商品类型、颜色、材质。
5. 增加可解释排序明细，让客户知道每个商品为什么被推荐。
6. 如果客户要求长期稳定运行，改接授权 API 或内部商品库。
