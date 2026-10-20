# 浏览器冒烟测试

[English](README.md) | [简体中文](README.zh-CN.md)

使用固定输入检查 Skill 脚本、模板和生成页面，可在本地和 CI 中运行，不调用模型。

## 测试内容

| Skill | 用例 | 检查内容 |
| --- | --- | --- |
| data-storytelling | [story-html](data-storytelling/story-html) | 组装 HTML 故事并渲染图表 |
| data-storytelling | [story-ppt](data-storytelling/story-ppt) | 组装 Web-PPT、渲染图表、前进及返回翻页 |

两个用例均检查图表画布非空、页面及资源错误、本地资源加载。PPT 翻页检查目标页面的位置和可见性。冒烟测试使用减少动态效果设置，不验收动画或叙事质量；截图用于排查问题，不做像素对比。

## 运行方式

在仓库根目录执行：

```bash
uv sync --locked
npm ci --prefix tests/browser --ignore-scripts
node tests/browser/node_modules/playwright/cli.js install chromium

uv run python tests/browser/scripts/smoke.py
uv run python tests/browser/scripts/smoke.py --skill data-storytelling
uv run python tests/browser/scripts/smoke.py --case story-ppt
```

Linux 缺少浏览器系统依赖时，使用 `install --with-deps chromium`。

报告、日志、输入、生成文件和截图保存在 `.cache/`。可用 `--output-dir PATH` 指定新的输出目录。任一用例失败时，命令返回非零退出码。

## 用例文件

每个 `<skill>/<case>/` 目录包含 `config.json`（构建配置）、`inputs/`（固定输入）和 `expectations.json`（必须执行的检查）。新增用例放在对应 Skill 目录下，runner 自动发现。
