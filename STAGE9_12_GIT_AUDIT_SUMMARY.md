# 阶段9到阶段12 Git 工作区边界整理与交付前审计总结

## 1. 审计目的

本总结记录阶段9到阶段12交付前的 Git 工作区边界审计结果，用于确认哪些文件属于阶段9到阶段12应提交范围，哪些文件属于运行产物或缓存不应提交，哪些文件属于禁止或高风险变更。

本次审计只做版本管理边界整理、文件归属审计和提交前检查；未执行 `git add`、`git commit` 或 `git push`。

## 2. 已执行检查命令

已执行并记录：

```text
git status
git diff --name-only
git diff --stat
git ls-files --others --exclude-standard
```

补充执行并通过：

```text
python -m unittest discover tests
python -m py_compile ui_streamlit.py
streamlit --version
python main.py
python -m src.product_fetcher
python -m src.crawler.review
python -m src.crawler.review_apply
```

测试结果摘要：

```text
python -m unittest discover tests：49 tests OK
python -m py_compile ui_streamlit.py：通过
streamlit --version：Streamlit, version 1.57.0
python main.py：通过
python -m src.product_fetcher：通过
python -m src.crawler.review：通过
python -m src.crawler.review_apply：通过
```

## 3. A类：建议提交文件

### 阶段9

```text
STAGE9_PLAN.md
STAGE9_SUMMARY.md
src/crawler/adapters/__init__.py
src/crawler/adapters/base.py
src/crawler/adapters/manual_csv_adapter.py
src/crawler/adapters/manual_json_adapter.py
src/crawler/adapters/static_page_adapter.py
src/crawler/review.py
src/crawler/pipeline.py
tests/test_stage9_adapters.py
tests/test_stage8_crawler.py
main.py
.gitignore
TASKS.md
```

### 阶段10

```text
STAGE10_PLAN.md
STAGE10_SUMMARY.md
src/crawler/review_apply.py
tests/test_stage10_review_apply.py
main.py
TASKS.md
```

### 阶段11

```text
STAGE11_PLAN.md
STAGE11_SUMMARY.md
src/crawler/review_template.py
src/crawler/review_validate.py
tests/test_stage11_review_template_validate.py
src/crawler/review_apply.py
TASKS.md
```

### 阶段12

```text
STAGE12_PLAN.md
ui_streamlit.py
tests/test_stage12_ui_smoke.py
TASKS.md
```

`requirements.txt` 已包含且仅包含一条 `streamlit`，审计时无 diff，不建议加入阶段9到阶段12提交清单。

## 4. B类：不建议提交文件

以下属于运行产物或缓存，原则上不提交：

```text
outputs/*.json
outputs/*.docx
outputs/stage*_test_workspace/
logs/*.log
__pycache__/
**/__pycache__/
.pytest_cache/
*.pyc
```

审计确认 `.gitignore` 已覆盖上述主要运行产物和缓存；`git ls-files --ignored --exclude-standard --others` 能列出这些被忽略文件，说明它们不会默认进入提交。

## 5. C类：高风险或需解释文件

以下文件有 diff，但可归属到阶段9到阶段11，不是阶段12新增越界：

```text
main.py
src/crawler/pipeline.py
tests/test_stage8_crawler.py
.gitignore
TASKS.md
```

归属说明：

1. `main.py`：属于阶段10/阶段11复核回填闭环，支持优先使用 `reviewed_products.json` 并返回复核相关输出路径。
2. `src/crawler/pipeline.py`：属于阶段9/9.1，新增人工复核清单、采集报告 summary 和免责声明。
3. `tests/test_stage8_crawler.py`：属于阶段9对采集报告 summary 和人工复核清单输出的回归测试补充。
4. `.gitignore`：属于阶段9.1交付审计和运行产物边界整理，覆盖输出、日志和缓存。
5. `TASKS.md`：属于阶段9到阶段12总控文档更新，变更较大，建议随阶段9到阶段12合并提交并在提交说明中解释。

## 6. 禁止文件检查

审计确认以下文件未触碰：

```text
app.py
src/doc_writer.py
src/response_builder.py
src/product_loader.py
src/product_ranker.py
config/crawler_config.json
data/seed_urls.json
data/sample_products.json
STAGE1_SUMMARY.md
STAGE2_SUMMARY.md
STAGE3_SUMMARY.md
STAGE4_SUMMARY.md
STAGE5_7_SUMMARY.md
STAGE8_SUMMARY.md
```

阶段9到阶段12审计范围内未发现禁止文件 diff。

## 7. 阶段12边界检查

阶段12边界检查结果：

1. `ui_streamlit.py` 只调用现有函数，不重写业务逻辑。
2. `tests/test_stage12_ui_smoke.py` 覆盖导入安全、`main` 或 `render_app` 存在、旧接口仍存在。
3. `TASKS.md` 显示阶段12已完成，阶段13真实样例数据验收待开始。
4. `requirements.txt` 已有 `streamlit`，未重复添加。
5. 阶段12未修改禁止文件。
6. 阶段12未新增上传功能。
7. 阶段12未进入阶段13真实样例数据验收。

## 8. 安全红线检查

审计确认：

1. 没有把采集、复核、推荐结果称为最终采购结论。
2. 出现“最终采购结论”的位置均为“不代表”“非”“禁止”等免责声明语境。
3. 没有新增淘宝、京东、1688、得物默认适配器。
4. 没有绕登录、验证码、风控、Cookie、代理池、个人信息、自动下单相关逻辑。
5. 没有新增上传功能、后台、数据库、登录、真实采购或自动下单能力。

## 9. 建议 Git Add 清单

如果合并提交阶段9到阶段12，建议执行：

```text
git add .gitignore TASKS.md main.py src/crawler/pipeline.py tests/test_stage8_crawler.py
git add STAGE9_PLAN.md STAGE9_SUMMARY.md
git add STAGE10_PLAN.md STAGE10_SUMMARY.md
git add STAGE11_PLAN.md STAGE11_SUMMARY.md
git add STAGE12_PLAN.md
git add src/crawler/adapters
git add src/crawler/review.py src/crawler/review_apply.py src/crawler/review_template.py src/crawler/review_validate.py
git add tests/test_stage9_adapters.py tests/test_stage10_review_apply.py tests/test_stage11_review_template_validate.py tests/test_stage12_ui_smoke.py
git add ui_streamlit.py
```

不建议加入：

```text
requirements.txt
outputs/
logs/
__pycache__/
src/__pycache__/
tests/__pycache__/
.pytest_cache/
*.pyc
data/seed_urls.json
data/sample_products.json
config/crawler_config.json
```

## 10. 建议 Commit Message

如果合并提交阶段9到阶段12，建议：

```text
complete stages 9 to 12 crawler review and streamlit ui workflow
```

如果只提交阶段12，建议先拆分阶段12文件后再使用：

```text
complete stage 12 streamlit operation ui
```

## 11. 是否可以进入阶段13

审计结论：阶段9到阶段12边界清楚，测试通过，可以进入阶段13。

建议进入阶段13前先完成阶段9到阶段12提交，避免真实样例数据验收产生的新运行产物、真实数据变更和阶段9到阶段12代码改动混在一起。

## 12. 残余风险

1. 阶段9到阶段12审计时，`TASKS.md` 变更较大，建议在提交说明中明确它是阶段9到阶段12总控状态更新。
2. 阶段12采集验证基于空 `seed_urls.json`，只能证明空采集路径正常，不代表真实 URL 验收完成。
3. 本地存在大量 ignored 运行产物和缓存，虽然不会进入提交，但交付前可按明确范围另行清理。
4. 若后续已进入阶段12.5或阶段13，应单独审计这些新增改动，不应混入阶段9到阶段12提交。
