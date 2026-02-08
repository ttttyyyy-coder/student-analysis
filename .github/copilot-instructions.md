<!-- .github/copilot-instructions.md: 指南用于指导 AI 编码代理在本仓库中迅速且安全地工作 -->
# 项目速览（给 AI 代理的快速上手说明）

本仓库是一个基于 Streamlit 的“智慧评价审计系统”，主要文件：`app.py`。运行入口为 `main()`（通过 `if __name__ == "__main__": main()` 调用）。

关键依赖在 `requirements.txt`，主要依赖包括 `streamlit`, `pandas`, `plotly`, `xlsxwriter` 等。

## 一、总体架构与数据流（必须知）
- 前端：使用 `streamlit` 渲染 UI，大量样式通过内联 HTML/CSS 写在 `app.py` 的 `st.markdown` 中。
- 输入：用户通过侧边栏上传 `.csv` 或 `.xlsx` 文件（`st.sidebar.file_uploader`）。
- 加载器：文件由 `UniversalLoader.load_file(file)` 解析——支持多种编码尝试（`utf-8-sig`, `gb18030`, `gbk`, `utf-16`），也会在 Excel 中尝试定位包含“姓名/学号/进度/时长/成绩”等关键词的表头行。
- 核心计算：`AuditCore` 负责列映射（`_map_columns`）、时长解析（`_parse_time`）与审计逻辑（`execute_audit`）。此函数输出 `res` DataFrame，包含 `进度/时长/成绩/讨论/证据链/异常原因/学习群体` 等字段。
- 展示：根据侧边栏导航渲染若干视图（Dashboard、深度挖掘、异常列表、未完结名单、原始数据表），并用 Plotly 绘图（`plotly.express`）与 Excel 导出（`xlsxwriter`）。

## 二、项目内重要文件与示例位置（供修改或扩展时参考）
- 入口：`app.py` — 整个应用逻辑集中在此文件。
- 文件解析器：`UniversalLoader.load_file` — 修改导入策略或新增编码支持请在此处。
- 审计核心：`AuditCore.execute_audit` — 所有判断阈值（如秒刷逻辑、群体划分）都在这里；若要调整风险判定、标签或聚类逻辑，应修改此函数或新增参数化配置。
- 时间解析：`AuditCore._parse_time` — 解析中文时间描述（例如“1时30分”、“45分钟”），对新增格式要谨慎扩展。
- 导出：在异常与未完结视图中使用 `pd.ExcelWriter(..., engine='xlsxwriter')` 写入内存 `BytesIO`，供 `st.download_button` 下载。

## 三、运行、调试与常用命令
- 本地运行（推荐虚拟环境）：
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
- 主要运行错误与排查点：
  - 若弹出“未找到有效表头”，说明 Excel 文件的表头定位逻辑未匹配，应检查文件中是否包含中文关键词（例如“姓名”“进度”）或调试 `UniversalLoader` 的前20行扫描。具体提示在 UI 中会以 `st.error`/`st.warning` 显示。
  - 若图表渲染出错，通常是因为 `audit_df` 缺少绘图列（检查 `AuditCore` 输出列名是否为 `时长/进度/成绩/讨论`）。

## 四、项目约定与编码/编辑指南（给 AI 代理的行为规则）
- 仅在 `app.py` 中做最小范围改动：优先修改封装好的方法（`UniversalLoader`、`AuditCore`）；避免大范围变动 UI 样式字符串（HTML/CSS）除非需要视觉调整。
- 保持中文 UI 文案风格与 emoji 标签一致（系统中大量使用中文提示与 emoji，例如 `🚨AI:秒刷`、`🟢正常`），不要随意删除或转换为英文。
- 在更改阈值或判定逻辑时：
  - 写清楚变更理由，并保持向后兼容（新增可选参数或常量而不是替换硬编码值）。
  - 在 `AuditCore.execute_audit` 添加注释说明阈值来源与含义。
- 不要引入对外部服务或数据库，当前应用为单文件、无外部后端依赖的静态分析/可视化工具。

## 五、常见编辑场景与示例修复（可直接应用）
- 修复“未完结统计”比较错误：代码中已将 `pd.to_numeric(...).fillna(0) < 99.9` 用于筛选；若需更严格条件，请在 `main()` 的计算处调整。
- 增加新的图表：在对应视图（例如“深度数据挖掘”tab）创建 Plotly 图后使用 `st.plotly_chart(fig, use_container_width=True)`。参考已有 `fig_clus`, `fig_hist` 的用法。

## 六、安全与测试注意事项
- 仓库当前没有单元测试；在修改 `UniversalLoader` 或 `AuditCore` 时，建议本地用几个典型导出文件（CSV/Excel）手工验证。保持对 `None`/空表的保护（应用中已有早期返回与提示）。

## 七、需要进一步信息？
如果你希望我把某些硬编码阈值提取到配置文件（如 `config.py`），或把 `AuditCore` 拆成更小的模块并加单元测试，请说明偏好（分支策略、是否保留中文注释等）。

---
请告知是否需要更详细的“修改示例”或希望我把阈值常量化为 `settings.py`（我可以直接创建 PR）。
