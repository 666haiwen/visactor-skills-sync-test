# 豆包能力与本地渲染

本包自带场景构建器与小型渲染入口，不需要安装完整 VInfo Skill，也没有运行时跨 Skill 文件依赖。

## 宿主能力

- 搜索、文档读取、图片检索：使用当前实际暴露的工具，保留原文和图片来源，不假定某个工具名一定存在。
- 新插图：宿主安装 `doubao-creative-design` 时读取其入口和当前工具合同，生成明确标注的插图或装饰素材；不让生图模型代写事实文字与数值，不用整张海报图片代替可编辑 schema。
- 素材加工：按需发现已安装的 `byted-mediakit-image` 及其 shared 依赖；人物抠图的额外要求见人物 Skill 引用。其他场景无需强制依赖 MediaKit。
- 自检：可用宿主 `artifact-preview` 或截图工具查看导出的 PNG。能力缺失时说明缺口，不输出伪造的成功结果。

## 运行条件

Python ≥3.10；素材转换需要 Pillow，PNG 导出需要 Python Playwright 与 Chromium。构建器使用本地图片并将其内嵌，不依赖远程图片跨域或短期下载链接。

在宿主允许安装依赖时，可在隔离环境中执行 `python -m pip install -r /Skill实际路径/requirements.txt` 和 `python -m playwright install chromium`；已有浏览器可通过 `--browser /实际/浏览器路径` 或 `CHROME_PATH` 指定。脚本不自动安装软件、下载浏览器或写入鉴权。

```bash
python scripts/build.py --brief brief.json --output output
python scripts/render.py --schema output/page-01.schema.json --html output/page-01.html --png output/page-01.png
```

场景提供 `assets/runtime.json` 时，HTML 优先使用其中的固定版本 `url`；否则页级 HTML 默认加载固定版本 `@dp/vinfo-graphics@0.12.4` 的 UMD SDK：
`https://sf-unpkg-src.bytedance.net/@dp/vinfo-graphics@0.12.4/dist/index.umd.js`。

豆包沙箱是否能访问该 CDN 需要部署时验证；不可访问时用 `--runtime-js /实际/index.umd.js` 提供与该场景版本一致的 SDK。它会复制到 HTML 同目录。浏览器渲染必须通过 `validatePageWithZod`，等待图片、字体、`renderPage(...).ready` 及后续画布像素稳定，再允许截图。

生成 HTML 本身不代表 PNG 已成功。检查 `__VINFO_READY__` / `__VINFO_ERROR__`；失败时修正依赖或输入，不能把空白截图当结果。浏览器或中文字体缺失时明确指出；安装宿主许可的中文字体后重新渲染。

场景包可通过 `assets/fonts.json` 内嵌获授权的 WOFF2，或通过 `assets/render-setup.js` 在渲染前加载字体 CDN。具体来源、等待与回退规则以场景字体约定为准；`__VINFO_FONTS__` 保存加载结果。未配置专用字体的场景沿用其 schema 字体栈。

## 修改与交付

优先改 brief 后重新构建。定制版式可修改生成的标准 v3 schema，但保留真实 `type/id/style` 结构，图片用 `image`，人物叙事用 `storyline`。无需新增渲染器或私有 node type。

图片引用已经内嵌；默认页 HTML 仍依赖 SDK 网络；采用 CDN 字体的场景还需访问字体服务。若采用本地 SDK，交付 HTML 时连同 SDK；导出 PNG 无此依赖。旅行 `book.py` 将 PNG 再内嵌成完全离线的单个 HTML。

可视验收检查标题与正文可读、人物/菜品没有误裁、所有来源与估算标记保留、图表数值一致。附上 schema 与 `sources.json`，便于追溯和修改。
