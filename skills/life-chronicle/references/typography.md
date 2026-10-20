# 字体与渲染

照片墙、中心网格、环形叙事的横竖版统一使用飞书镜像中的 **Noto Serif SC（思源宋体系）**，正文400、标题700。Skill 不包含字体二进制，不依赖其他 Skill 的字体目录。

- HTML 的 `assets/render-setup.js` 插入字体 stylesheet `<link>`，从 `miaoda.feishu.cn/fonts/css2` 加载；不直连 `fonts.googleapis.com`。这里只请求该场景需要的 Serif 字体。
- 页面与所有文字节点使用 `"Noto Serif SC","Songti SC","STSong",serif`。Canvas 不继承外层 CSS，因此 schema 也必须设置字体。
- 渲染前等待 stylesheet 和页面所需文字的400／700字重加载，最多20秒。`window.__VINFO_FONTS__` 记录状态和实际匹配的字体字重。CDN 会按客户端返回不同格式；Chromium 验证中400／700均成功加载，命令行请求可能只返回常规 TTF。以实际浏览器结果为准。
- CDN 不可达时移除 stylesheet，按系统字体栈渲染并记录 `status: fallback`，避免加载迟到导致截图变化。交付前检查状态；发生回退应如实说明。无宋体的宿主最终使用浏览器 serif，不能保证完全相同的字形与换行。
- HTML／由 HTML 截图或打印的 PDF 需要联网加载字体；PNG 出图后无需联网。Word、PPT、PIL 直接绘字不使用该 CDN 加载流程。

字体变化可能影响换行，检查标题、长日期和正文容量。显式 `template: storyline` 保留 SDK 自有字体：SDK 0.12.4 的内部事件文字不继承页面字体，不把它计入上述覆盖范围。
