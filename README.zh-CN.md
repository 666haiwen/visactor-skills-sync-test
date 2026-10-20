# VisActor Skills

[English](README.md) | [简体中文](README.zh-CN.md)

面向 VisActor 可视化生态的 Agent Skills。通过可独立安装的 Skills 制作数据故事、杂志图文和人物志海报。VChart 和 VTable Skill 在各自的库仓库中维护。

## Skills

| Skill | 能力 | 维护位置 |
| --- | --- | --- |
| [VChart Skill](https://github.com/VisActor/VChart/blob/develop/skills/vchart-development-assistant/SKILL.md) | 图表生成、问题诊断、图片还原和 React 集成 | [VisActor/VChart](https://github.com/VisActor/VChart) |
| [VTable Skill](https://github.com/VisActor/VTable/blob/develop/skills/vtable-development-assistant/SKILL.md) | 明细表、透视表与透视图、交互和问题诊断 | [VisActor/VTable](https://github.com/VisActor/VTable) |
| [data-storytelling](skills/data-storytelling/SKILL.md) | 数据分析与叙事设计、滚动故事、HTML 报告和 Web-PPT | 本仓库 |
| [editorial-magazine](skills/editorial-magazine/SKILL.md) | 杂志图文：新闻、生平、穿搭、旅行、时序故事与科普，导出 HTML / PNG | 本仓库 |
| [life-chronicle](skills/life-chronicle/SKILL.md) | 人物生平海报：照片墙、中心网格、照片环与可编辑时间线 | 本仓库 |

每个 Skill 都包含完整指令、本地参考资料、模板和脚本。无需额外安装 VisActor CLI、MCP 服务，也无需为 Skill 单独配置模型 Key 或访问 VisActor 托管 API。模型能力由宿主 Agent 提供。

**推荐直接在 Codex 或 Claude Code 中使用 Skills。** 模型访问与工具执行由你使用的 Agent 提供。其他兼容的 Agent 也可以尝试使用，目前不提供专门的接入说明。

## 安装

在你准备使用 Skills 的项目目录中执行：

```bash
npx skills add VisActor/VChart --skill vchart-development-assistant
npx skills add VisActor/VTable --skill vtable-development-assistant
npx skills add VisActor/skills --skill data-storytelling
npx skills add VisActor/skills --skill editorial-magazine
npx skills add VisActor/skills --skill life-chronicle
```

按照安装器提示选择 Codex 或 Claude Code。每个 Skill 都可以按需单独安装。更多安装选项见 [Skills CLI 说明](https://github.com/vercel-labs/skills#usage)。

运行要求：

- Node.js 和 npm，用于执行上述安装命令。
- 具备文件系统和 Shell 工具的 Agent，以及该 Agent 自身的模型访问权限。
- data-storytelling 需要 Python 3.10+ 和 Node.js（校验 JavaScript），Python 脚本使用标准库。VChart/VTable Skill 的运行要求见各自仓库。
- 浏览器和网络连接，用于打开生成的 HTML。data-storytelling 通过公开的 unpkg CDN 加载固定版本的 VSeed、VChart、VTable 和 GSAP。

杂志图文与人物志另需 Python 3.10+、Pillow、Playwright 及 Chromium/Chrome；按所选 Skill 的 `requirements.txt` 安装依赖。字体默认从飞书镜像 CDN 加载，失败时使用系统字体；人物志另加载固定版本 VInfo SDK，详见其[环境说明](skills/life-chronicle/references/environment.md)。图片检索、生图与抠图依赖宿主能力；杂志模板只附占位素材，制作时需要替换。

## 使用

安装后，在 Agent 中指定所需 Skill，并提供你的数据。例如：

- “用 VChart 对比这个 CSV 中各地区、各季度的销售额，给我可编辑的源码和 HTML。”
- “使用这个文件中的全部数据，用 VTable 创建一个支持排序的明细表。”
- “使用 data-storytelling，向增长负责人解释这个 CSV 的留存变化，生成可分享的 HTML 故事。”

data-storytelling 由当前 Agent 生成 VSeed 配置，再用本地脚本组装；不依赖托管图表生成服务。图片生成使用宿主能力，没有生图工具时采用计划声明的 fallback。Web-PPT 是浏览器演示稿，不是 `.pptx`。

生成的 JavaScript/HTML 是可执行代码。请在本地预览自己生成或已审查的产物；评测浏览器并不是用于执行任意不可信提交的安全沙箱。

## 开发与维护

本节面向需要修改 Skills 或运行本地测试的贡献者。默认分支和主维护分支均为 `develop`，请先阅读 [贡献指南](CONTRIBUTING.md)。

### 从本地仓库安装

在本地仓库根目录执行，安装当前工作副本中的 Skill：

```bash
npx skills add ./skills/data-storytelling
npx skills add ./skills/editorial-magazine
npx skills add ./skills/life-chronicle
```

也可以将 Skill 的完整目录复制到 Agent 的技能目录中，包括参考资料、模板和脚本，不要只复制 `SKILL.md`。Codex 和 Claude Code 的调试工作区准备方式见 [本地调试指南](docs/debugging.md)。修改 Skill 后，请先更新安装副本，再重新测试。

### 回归测试

Python 维护环境要求 Python 3.12+ 和 [uv](https://docs.astral.sh/uv/)：

```bash
uv sync --locked
uv run pytest tests -q
uv run ruff check skills tests evals/scripts
```

固定浏览器 smoke 用例按 Skill 集中在 [evals/smoke/](evals/smoke/README.zh-CN.md)，每个用例的配置、输入和验收文件放在一起。按指南准备浏览器后，用 `uv run python evals/scripts/smoke.py` 执行全部用例，也可通过 `--skill data-storytelling` 或 `--case story-ppt` 单独选择。

### 通过模型 API 调试任务

轻量 harness 可通过 OpenAI 兼容的 Chat Completions 接口加载本仓库 Skill，执行固定用例或自定义任务，并保存请求、工具调用、用量和产物日志。它适合有限步骤的脚本与任务调试，不推荐用于数据叙事端到端评测；完整任务请使用 Codex 或 Claude Code。

配置和运行方式见 [评测说明](evals/README.zh-CN.md)。[用例目录](evals/cases/README.zh-CN.md) 包含 5 个数据叙事任务，浏览器 smoke 包含 HTML 故事和 Web-PPT 两条链路。模型任务不在 CI 中运行，调用模型可能产生费用。

## 版本管理

本仓库维护的 Skills 按整个仓库统一管理版本，每次正式发布使用 Git tag 标识包含 Skill 指令、参考资料、模板和脚本的版本快照。VChart 和 VTable Skill 的版本由各自仓库管理。

反馈问题或复现结果时，请记录发布 tag 或 commit SHA；分支内容会随开发变化。VTable `1.26.8` 等依赖版本表示底层库的版本，不是 Skill 的发布版本。历史 VMind SDK 的 tag 保持不变，仍归属于原 SDK。

## VMind 历史版本

原 VMind SDK 不再维护，其代码和文档仍可通过 [历史发布版本](https://github.com/VisActor/skills/releases) 获取。

[MIT 许可证](LICENSE)
