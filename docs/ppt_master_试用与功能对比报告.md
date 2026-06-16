# PPT Master 与当前 `pptx_gen` 试用与功能对比报告

## 1. 目标与约束

本次任务目标：

- 实际试用 `c:\AMD\pptx_gen\ppt-master-main`
- 与当前项目 `c:\AMD\pptx_gen` 做功能和体验对比
- 输出一份可直接阅读的 Markdown 报告
- **不修改任何源码**

说明：本次我按刚记录的“对比评估需求”执行，全程只做了文档阅读、安全命令执行、临时产物输出与报告整理，没有修改任何现有源码文件。

---

## 2. 试用方法

本次对比分成三部分：

### 2.1 文档与入口检查

我阅读并核对了：

- 当前项目 `README.md`
- 当前项目 `pyproject.toml`
- 当前项目 `pptx_gen/cli.py`
- 当前项目 `pptx_gen/pipeline/runner.py`
- `ppt-master-main/README.md`
- `ppt-master-main/skills/ppt-master/SKILL.md`
- `ppt-master-main/skills/ppt-master/scripts/README.md`
- `ppt-master-main/skills/ppt-master/scripts/docs/project.md`
- `ppt-master-main/skills/ppt-master/scripts/docs/svg-pipeline.md`
- `ppt-master-main/skills/ppt-master/requirements.txt`

### 2.2 安全试跑原则

试跑只做以下两类动作：

- **只读验证**：`--help`、校验、信息查看、质检
- **临时输出**：把分析结果和试跑产物写到 `output/compare_trials/` 下

没有改动任何现有源码，也没有覆盖 `ppt-master-main/examples/` 里的原始导出结果。

### 2.3 重点对比维度

本次重点比较：

- 模板解析能力
- 模板直填能力
- 端到端导出能力
- 图表/图形方案
- 可编辑性
- 对外部依赖的敏感程度
- 工作流复杂度

---

## 3. 实际执行结果

## 3.1 `ppt-master-main` 实测结果

### A. 入口脚本可启动

已实际执行：

- `python ...project_manager.py --help`
- `python ...template_fill_pptx.py --help`
- `python ...svg_to_pptx.py --help`
- `python ...source_to_md/ppt_to_md.py --help`

结论：

- 这些入口在当前机器上都能正常启动
- `ppt-master` 的脚本体系是完整的，不是“只有文档、没有真实入口”

### B. 示例工程校验可运行

已实际执行：

```bash
python skills/ppt-master/scripts/project_manager.py validate examples/ppt169_glassmorphism_demo
python skills/ppt-master/scripts/project_manager.py info examples/ppt169_glassmorphism_demo
```

结果：

- 校验通过，项目结构有效
- 仅有一个警告：目录名缺少日期后缀 `_YYYYMMDD`
- 项目信息可正常读取

这说明 `ppt-master` 已经具备比较成熟的“工程目录约束 + 体检能力”。

### C. SVG 质量检查可运行

已实际执行：

```bash
python skills/ppt-master/scripts/svg_quality_checker.py examples/ppt169_glassmorphism_demo
```

结果：

- 共检查 12 个 SVG 文件
- 0 个错误
- 12 个警告
- 警告主要是：`spec_lock.md` 中未锁定某些字体族，出现 `spec_lock drift`

这说明：

- `ppt-master` 有一套明显更成熟的 SVG 质检体系
- 但它自己的示例项目也不是完全“零告警”状态
- 它的质量体系很强，但同时也带来了更严格的流程约束

### D. 用同一个 `templete.pptx` 做模板分析

已实际执行：

```bash
python skills/ppt-master/scripts/template_fill_pptx.py analyze templete.pptx -o output/compare_trials/ppt_master_template/slide_library.json
python skills/ppt-master/scripts/pptx_template_import.py templete.pptx --manifest-only -o output/compare_trials/ppt_master_template/template_import
```

结果：

- `template_fill_pptx.py analyze` 成功输出 `slide_library.json`
- 分析到 **48 页**
- `pptx_template_import.py --manifest-only` 成功输出 `manifest.json` 和 `summary.md`
- `manifest.json` 统计如下：
  - **48 slides**
  - **14 layouts**
  - **1 master**
  - **4 assets**

这说明：

- `ppt-master` 对 PPTX 模板的理解深度，明显不只是“按页抽元素”
- 它还会记录：
  - slide size
  - theme
  - assets
  - layouts
  - masters
  - slides
- 也就是说，它的模板理解更接近“PPTX 结构级导入”，不是单纯内容回填

### E. 模板直填规划链路可运行

已实际执行：

```bash
python skills/ppt-master/scripts/template_fill_pptx.py scaffold output/compare_trials/ppt_master_template/slide_library.json -o output/compare_trials/ppt_master_template/fill_plan.json --slides "1,3,4"
python skills/ppt-master/scripts/template_fill_pptx.py check-plan output/compare_trials/ppt_master_template/slide_library.json output/compare_trials/ppt_master_template/fill_plan.json -o output/compare_trials/ppt_master_template/check_report.json
```

结果：

- `fill_plan.json` 成功生成
- 计划文件包含：
  - `schema`
  - `source_pptx`
  - `slides`
- 计划页包含：
  - `source_slide`
  - `purpose`
  - `replacements`
  - `table_edits`
  - `chart_edits`
- `check-plan` 结果：
  - `ok = 8`
  - `warn = 0`
  - `error = 0`

这说明：

- `ppt-master` 已经形成了一条比较完整的“模板分析 → 填充计划 → 计划校验 → 实际套用”的工作流
- 这条链路对人工控制和逐步确认更友好

### F. 示例导出能力可运行

已实际执行：

```bash
python skills/ppt-master/scripts/svg_to_pptx.py examples/ppt169_glassmorphism_demo -s final -o output/compare_trials/ppt_master_export/glassmorphism_demo_trial.pptx --no-cache
```

结果：

- 成功导出
- 12 / 12 页全部成功
- 输出文件存在
- 输出文件大小约 **7.49 MB**
- 导出模式为 **Native DrawingML shapes**
- 自动带入 **speaker notes**

这是本次试用里最关键的一点：

**`ppt-master` 在当前机器上，真实具备“从 SVG 工程导出到可编辑 PPTX”的能力。**

---

## 3.2 当前 `pptx_gen` 实测结果

### A. CLI 入口正常

已实际执行：

```bash
python -m pptx_gen --help
```

结果：

- 入口可正常运行
- 当前命令体系清晰，包含：
  - `extract-template`
  - `generate-pages`
  - `render-mermaid`
  - `build-ppt`
  - `run-pipeline`

### B. 模板抽取可运行

已实际执行：

```bash
python -m pptx_gen extract-template --template templete.pptx --output output/trial_template_rules_compare.json
```

结果：

- 成功输出模板规则
- 共 **48 页**
- 输出结构以页面为核心，第一页关键字段包括：
  - `page_no`
  - `page_name`
  - `page_purpose`
  - `supports_mermaid`
  - `title`
  - `elements`

这说明：

- 当前项目的模板抽取是有效的
- 但抽取粒度主要围绕“给大模型生成页面 JSON 所需的约束”
- 它不是像 `ppt-master` 那样偏 PPTX 结构级导入，而是偏“页面生成约束层”

### C. 完整流水线真实失败

已实际执行：

```bash
python -m pptx_gen run-pipeline --template templete.pptx --requirement req.txt --output-dir output/compare_trials/pptx_gen_pipeline --max-workers 4
```

结果：

- 页面 JSON 已成功生成：**48 个 page_xx.json**
- Mermaid 中间文件已生成：**1 个 `.mmd`**
- PNG 渲染结果：**0 个**
- 最终 PPT：**未生成**

实际失败点：

- 失败在 Mermaid 渲染阶段
- 当前环境命中的 CLI 是 **Python 版 `mmdc`（PhantomJS）**
- 它对 `classDiagram` 和中文兼容较差
- 它会出现：
  - `stderr` 报错，但仍显示“converted successfully”
  - 空白图假成功

当前项目里我之前已经加了失败检测，所以这次不会再静默产出错误 PPT，而是会明确失败。

这说明：

- 当前 `pptx_gen` 的“页面生成前半段”已经能跑
- 但“图形渲染 + 最终导出”仍被 Mermaid 工具链卡住

---

## 4. 功能对比结论

| 对比项 | `ppt-master` | 当前 `pptx_gen` | 结论 |
|---|---|---|---|
| 输入来源 | PDF / DOCX / PPTX / Excel / URL / Markdown / 对话文本 | 当前主流程以 `requirement.txt` 为主 | `ppt-master` 更全面 |
| 模板解析深度 | 到 slide / layout / master / theme / assets 层级 | 以页面元素和生成约束为主 | `ppt-master` 更深 |
| 模板直填 | 有完整 analyze / scaffold / check-plan / apply | 以页面 JSON 回填模板为主，没有独立 fill plan 工作流 | `ppt-master` 更成熟 |
| 图形方案 | 主路线是 SVG → Native PPTX | 主路线是 Mermaid → PNG → 插入 PPT | `ppt-master` 可编辑性更强 |
| 最终图形可编辑性 | 高，Native DrawingML | Mermaid 图是图片，不可像形状那样编辑 | `ppt-master` 更强 |
| 动画 / 旁白 / 转场 | 支持 | 当前没有完整支持 | `ppt-master` 明显领先 |
| 质量检查 | 项目校验、SVG 质检、坐标检查、spec_lock 约束 | 当前主要靠流程本身和少量失败检测 | `ppt-master` 更完整 |
| 工作流复杂度 | 高，强依赖 agent 纪律与多阶段流程 | 低，更像脚本型流水线 | `pptx_gen` 更容易上手 |
| 与固定模板结合 | 有，但偏“模板导入 + 计划填充” | 很贴近“模板解析 + 内容生成 + 回填” | 当前项目更聚焦你的原始需求 |
| 对外部图形依赖敏感度 | 不依赖 Mermaid | 强依赖 Mermaid CLI | 当前项目短板明显 |
| 当前机器实测最终导出 | 成功 | 失败 | 当前阶段 `ppt-master` 更可用 |

---

## 5. `ppt-master` 相对当前项目的优点

- **功能覆盖更完整**
  - 不只是做 PPT 组装，还覆盖：
  - 多格式输入
  - 项目初始化
  - 模板导入
  - SVG 质检
  - 动画
  - 旁白音频
  - 最终原生 PPTX 导出

- **可编辑性更强**
  - 它的主路线是把 SVG 转成原生 DrawingML 形状
  - 对比当前项目的 Mermaid PNG，这一点是本质优势

- **工程化程度更高**
  - 有 `project_manager.py`
  - 有 `validate`
  - 有 `info`
  - 有独立 `check-plan`
  - 有 `svg_quality_checker.py`

- **模板能力更深**
  - 不只看单页元素，还能识别 layout / master / assets / theme
  - 对复杂模板和可复用模板体系更友好

- **现机实测可导出**
  - 这不是只看文档得出的结论
  - 我已经在你当前环境里把它的示例成功导成了 PPTX

---

## 6. `ppt-master` 相对当前项目的缺点 / 不适配点

这些不是说它不好，而是说**它不一定更适合你当前这个项目阶段**。

- **流程太重**
  - 它是一整套 skill / agent 工作流，不是一个轻量脚本
  - 有严格串行阶段
  - 有很多上下文约束
  - 对一个只想“把现有模板自动填内容”的项目来说，理解成本偏高

- **强依赖高质量 agent**
  - 它自己在文档里也强调：质量上限很依赖 Claude / 大上下文 / 图像模型
  - 如果只是想稳定做业务 PPT 自动化，这条路的成本比当前项目高

- **对非技术用户不够友好**
  - 里面有很多概念：
    - `design_spec.md`
    - `spec_lock.md`
    - `svg_output`
    - `svg_final`
    - `animations.json`
    - 各种 workflow
  - 对初学者来说会明显更重

- **主线不是“固定模板 + 需求文档 + 一键回填”**
  - 它擅长的是高自由度设计、SVG 页面生成、再导出到原生 PPTX
  - 你当前项目更像“业务模板生成器”，目标更窄，但也更聚焦

- **它自己的示例也并非完全无警告**
  - 这次实测 `svg_quality_checker` 就出现了 12 个 `spec_lock drift` 警告
  - 说明它虽然强，但流程本身也复杂，维护成本不低

---

## 7. 当前 `pptx_gen` 相对 `ppt-master` 的优点

- **更贴近你最初的业务目标**
  - 你的项目本质上是：
  - 解析固定模板
  - 按页生成结构化内容
  - 回填模板
  - 导出 PPT
  - 这个目标在当前项目里更直接

- **脚本链路更简单**
  - `extract-template`
  - `generate-pages`
  - `render-mermaid`
  - `build-ppt`
  - `run-pipeline`
  - 比 `ppt-master` 更容易理解和调试

- **页面约束更明确**
  - 当前模板规则输出本来就是给 LLM 按页生成内容用的
  - 对“固定模板约束生成”这个场景更自然

- **更容易做 MVP**
  - 如果目标是尽快做出一条能跑的模板填充链路
  - 当前项目比 `ppt-master` 更容易持续迭代

---

## 8. 当前 `pptx_gen` 的主要缺陷

这是这次对比里最值得重视的一部分。

- **Mermaid 是当前最大阻塞点**
  - 图形生成严重依赖 Mermaid CLI
  - 当前机器命中的 Python 版 `mmdc` / PhantomJS 不稳定
  - 直接导致完整流水线失败

- **图形不可编辑**
  - Mermaid 目前是渲染成 PNG 再插入 PPT
  - 图形最终不是 PowerPoint 原生形状
  - 这比 `ppt-master` 的 Native DrawingML 差很多

- **缺少完整的工程化体检工具**
  - 没有类似：
    - `project_manager validate`
    - `svg_quality_checker`
    - `check-plan`
    - 坐标校验工具

- **输入源能力弱**
  - 当前主流程还是围绕文本需求文件
  - 相比 `ppt-master`，缺少标准化的 PDF / DOCX / Excel / Web → Markdown / 文本入口

- **模板理解层级不够深**
  - 当前更偏“按页元素约束”
  - 还没有把 master / layout / theme / assets 的结构价值充分利用起来

- **功能上限较低**
  - 没有旁白
  - 没有动画配置
  - 没有 SVG / Native shape 级别的高保真图形导出
  - 视觉表达上限明显低于 `ppt-master`

---

## 9. 我建议你怎么取舍

### 如果你的目标是：尽快做出一个稳定的“模板自动填充工具”

建议：**继续以当前 `pptx_gen` 为主线。**

原因：

- 更聚焦
- 更简单
- 更容易迭代
- 更符合你现在“固定模板 + 文档内容 + 自动回填”的原始需求

但要优先补这几个点：

1. **先解决 Mermaid 工具链问题**
   - 切到 Node 版 Mermaid CLI
2. **补一个项目级校验命令**
   - 类似“检查模板、页面 JSON、渲染结果、最终输出是否完整”
3. **补一个模板填充前检查器**
   - 类似 `check-plan`，提前发现文本超框、表格过长、图片缺失
4. **逐步弱化 Mermaid 图片依赖**
   - 后续考虑 SVG 或原生形状路线

### 如果你的目标是：做更强、更高上限、可编辑性更好的 AI 生成 PPT 平台

建议：**认真借鉴 `ppt-master` 的设计。**

重点值得借鉴的不是“整个仓库照搬”，而是以下思想：

1. **模板导入深度**
   - 引入 layout / master / theme / assets 级理解
2. **质量检查链路**
   - 对输出做结构校验和质量体检
3. **中间产物可追踪**
   - 每一步都有明确文件产物，而不是只看最终成败
4. **从图片图形转向原生可编辑图形**
   - 这是和普通 AI PPT 工具拉开差距的关键

---

## 10. 最终结论

一句话总结：

**`ppt-master` 是一个能力更强、上限更高、已经能在当前机器上真实导出原生可编辑 PPTX 的完整体系；但它更重、更复杂、更依赖强 agent。当前 `pptx_gen` 更轻、更贴近你的原始业务目标，但目前被 Mermaid 渲染链路卡住，图形可编辑性也明显落后。`**

更具体地说：

- **如果看“当前机器上谁现在更能直接出结果”**：`ppt-master` 更强
- **如果看“谁更贴合你现在这个模板驱动项目的最短路径”**：`pptx_gen` 更贴合
- **如果看“谁的主要短板最致命”**：当前 `pptx_gen` 的 Mermaid 渲染问题最致命
- **如果看“谁值得被借鉴”**：`ppt-master` 很值得借鉴，但不建议整套照搬

---

## 11. 本次实际产物位置

本次试跑生成的临时产物位于：

- `output/compare_trials/ppt_master_template/slide_library.json`
- `output/compare_trials/ppt_master_template/template_import/manifest.json`
- `output/compare_trials/ppt_master_template/fill_plan.json`
- `output/compare_trials/ppt_master_template/check_report.json`
- `output/compare_trials/ppt_master_export/glassmorphism_demo_trial.pptx`
- `output/compare_trials/pptx_gen_pipeline/`
- `output/trial_template_rules_compare.json`

本报告文件位于：

- `ppt_master_试用与功能对比报告.md`
