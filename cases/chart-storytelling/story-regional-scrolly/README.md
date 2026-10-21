# story-regional-scrolly

使用 `chart-storytelling` 完成 [prompt.md](prompt.md) 中的任务。输入在 [inputs/](inputs/)，均为模拟测试数据；文件校验值见 [fixtures.json](fixtures.json)。

按[本地调试指南](../../../docs/debugging.md)准备独立工作目录，只复制提示词和输入交给 Agent。本文件供完成后验收使用。

## 验收要点

- 数据、计算口径、单位和文案一致；模拟数据标识清楚，不杜撰因果或来源。
- 计划、真实图表、素材/降级报告和最终 HTML 可追溯；人工检查可读性、布局和交互。
- 实际滚动每一步，确认主图状态变化与当前文字对应；不同正确叙事与样式均可接受。

## 交付文件

文件位于调试工作目录的 `outputs/` 下：

- `output.html`
- `runtime/plan.md`
- `runtime/dataset_map.json`
- `runtime/chart_specs.json`
- `runtime/spec_map.json`
- `runtime/asset_resolution_report.json`
- `runtime/resolved_asset_bindings.json`
- `runtime/page.json`
- `runtime/body.html`

允许不同的叙事、布局和视觉表达；按数据准确性、任务要求和实际交互验收，不要求复刻固定页面或像素一致。
