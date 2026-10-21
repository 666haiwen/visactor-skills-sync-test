# story-retention-deck

使用 `chart-storytelling` 完成 [prompt.md](prompt.md) 中的任务。输入在 [inputs/](inputs/)，均为模拟测试数据；文件校验值见 [fixtures.json](fixtures.json)。

按[本地调试指南](../../../docs/debugging.md)准备独立工作目录，只复制提示词和输入交给 Agent。本文件供完成后验收使用。

## 验收要点

- 数据、计算口径、单位和文案一致；模拟数据标识清楚，不杜撰因果或来源。
- 计划、真实图表、素材/降级报告和最终 HTML 可追溯；人工检查可读性、布局和交互。
- 月度留存从 91% 到 82%，下降 9 个百分点；新用户与企业客户留存相差 15 个百分点。
- 实际键盘翻页，至少三页，结尾收束且不溢出；HTML Web-PPT，不要求 pptx。

## 交付文件

文件位于调试工作目录的 `outputs/` 下：

- `output-ppt.html`
- `runtime/plan.md`
- `runtime/dataset_map.json`
- `runtime/chart_specs.json`
- `runtime/spec_map.json`
- `runtime/asset_resolution_report.json`
- `runtime/resolved_asset_bindings.json`
- `runtime/page.json`
- `runtime/slides.html`

允许不同的叙事、布局和视觉表达；按数据准确性、任务要求和实际交互验收，不要求复刻固定页面或像素一致。
