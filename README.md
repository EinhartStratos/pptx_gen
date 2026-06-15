# pptx_gen

## 项目简介

这是一个基于 Python 的 PPT 生成项目。

目标是把 `templete.pptx` 解析为一份适合脚本和大模型共同使用的模板规则 JSON，然后基于需求文档，按页调用大模型生成每页内容，最后汇总生成结果 PPT。

## 当前项目状态

当前工作区已确认存在以下文件：

- `templete.pptx`
- `docs/PRD.md`
- `requirements.txt`
- `pptx_gen/` Python 包

当前已完成以下首版代码：

- 模板规则解析模块
- 大模型请求与并发分页生成模块
- Mermaid 渲染模块
- PPT 组装与删页模块
- `python -m pptx_gen` 命令行入口
- Windows 环境下 `mmdc` 的 `.venv/Scripts` 自动定位与 UTF-8 渲染兼容处理
- 纯文本页面在正文超框时的同标题自动续页能力

## 当前已确认的模板事实

已对 `templete.pptx` 做结构核实，确认它是标准 Office Open XML 的 PPTX 包结构，包含：

- `ppt/presentation.xml`
- `ppt/slides/slide*.xml`
- `ppt/slides/_rels/slide*.xml.rels`
- `ppt/slideLayouts/*.xml`
- `ppt/slideLayouts/_rels/*.xml.rels`
- `ppt/slideMasters/*.xml`
- `ppt/theme/*.xml`

当前还确认到：

- 模板总页数为 48 页
- 页面中存在文本框
- 页面中存在图片元素
- 页面中存在表格元素
- 页面中存在分组图形
- 页面中存在连接线元素
- 当前模板包内未发现现成的 `notesSlides` 或 `notesMasters` 部件

当前业务已确认，V1 规则解析只读取 `ppt/slides/*.xml`，其他部件暂不作为模板规则来源。

## 规划中的功能模块

### 1. 模板规则提取

输入：

- `templete.pptx`

输出：

- `template_rules.json`

用途：

- 提取每页标题
- 提取标题位置和样式
- 提取所有页面元素类型、位置、尺寸和样式
- 为大模型生成页面内容提供结构化约束
- 为后续 PPT 回填脚本提供定位依据

### 2. 需求文档读取与结构化

输入：

- 纯文本需求文档

输出：

- 标准化需求文本

用途：

- 作为分页调用大模型时的全文输入
- V1 不做摘要和切片，避免信息失真

### 3. 按页调用大模型生成内容

输入：

- 需求文档全文
- 单页模板规则

输出：

- 单页内容 JSON
- 是否跳过该页的判断结果
- 跳过原因

用途：

- 每页独立生成文字、表格或 Mermaid 图定义
- 支持模板页按需生成，而不是强制每页都产出内容
- 支持并发调用模型，线程池大小可配置

### 4. 图形内容生成与渲染

输入：

- 大模型输出的 Mermaid 图定义

输出：

- PNG 图片

用途：

- 将流程图、架构图、时序图先由大模型输出为 Mermaid 文本
- 再由 Mermaid CLI 渲染成图片插入 PPT
- V1 不写备注栏，Mermaid 原文保存在中间文件中

### 5. PPT 组装与导出

输入：

- 模板 PPT
- 全部页面内容 JSON
- 图像渲染结果

输出：

- 最终生成的 PPT 文件

用途：

- 按模板位置回填文本、表格、图片和图形结果
- 输出最终可交付的演示文稿

## 当前代码目录结构

### `pptx_gen/template/`

- `parser.py`：解析 `templete.pptx`，抽取页面规则并输出 `template_rules.json`

### `pptx_gen/llm/`

- `prompts.py`：组织单页提示词
- `client.py`：封装 `mock` 和 `openai_compatible` 两种模型请求方式
- `generator.py`：按页并发生成 `page_xx.json`

### `pptx_gen/render/`

- `mermaid.py`：把 Mermaid 文本写入 `.mmd` 并调用 `mmdc` 渲染 PNG

### `pptx_gen/ppt/`

- `builder.py`：回填文本、表格、图片，并删除 `should_generate = false` 的页面

### `pptx_gen/pipeline/`

- `runner.py`：串联模板解析、分页生成、渲染和 PPT 输出

### `pptx_gen/`

- `config.py`：环境变量与路径配置
- `schemas.py`：共享数据结构
- `cli.py`：命令行入口
- `__main__.py`：支持 `python -m pptx_gen`

## 当前命令行入口

- `python -m pptx_gen extract-template --template templete.pptx --output output/template_rules.json`
- `python -m pptx_gen generate-pages --requirement requirement.txt --rules output/template_rules.json --output-dir output/pages --max-workers 4`
- `python -m pptx_gen render-mermaid --pages-dir output/pages --mermaid-dir output/mermaid --rendered-dir output/rendered`
- `python -m pptx_gen build-ppt --template templete.pptx --rules output/template_rules.json --pages-dir output/pages --output output/generated.pptx`
- `python -m pptx_gen run-pipeline --template templete.pptx --requirement requirement.txt --output-dir output --max-workers 4`

## 当前阶段结论

当前最合理的推进顺序是：

1. 先完成模板规则抽取和 JSON 结构定义
2. 再定义单页大模型输入输出协议
3. 再落地 Mermaid 渲染方案
4. 再实现并发调度和 PPT 组装
5. 最后补充删页逻辑与异常处理

## 当前已识别风险

### 1. 部分样式可能未完全体现在 slide XML 中

当前业务已确认 V1 只解析 `ppt/slides/*.xml`，因此如果个别样式依赖其他部件，后续需要按需补充解析。

### 2. 每页直接读取完整需求文档，成本会增加

当前已确认优先使用全文输入，虽然能减少信息失真，但会增加调用成本与响应时间。

### 3. 表格超长需要主要依赖提示词限制

当前策略是不优先做后处理，因此表格容量控制要在提示词和规则字段中设计好。

### 4. Mermaid 渲染依赖外部工具链

需要 Mermaid CLI 才能稳定将 `.mmd` 渲染为 PNG，后续脚本需要处理这部分依赖。

当前代码已兼容两类常见运行方式：

- 系统 `PATH` 中可直接找到 `mmdc`
- `mmdc` 安装在当前 `.venv/Scripts` 中，由脚本自动定位并以 UTF-8 环境调用

### 5. 纯文本页的自动续页仍属于保守策略

当前仅对“纯文本页面、只有一个主正文框、模板说明明确写有可分多页”的场景启用自动续页。

这样可以降低误拆分页的概率，但表格页、图文混排页暂不做自动拆页，后续如果需要可以再继续增强。

## 下一步建议

- 先实现模板规则提取脚本
- 再定义单页生成 JSON 协议和提示词限制
- 然后实现 Mermaid 渲染、图片插入和并发调度

## 本次更新说明

本 README 基于当前实际检查结果创建，用于记录项目目标、模板事实、规划模块和已识别风险，便于后续继续开发与交接。
