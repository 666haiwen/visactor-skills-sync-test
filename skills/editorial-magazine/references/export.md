# 静态 HTML → PNG

## 小合同

完整 HTML 包含 UTF-8、内联 CSS 和一个或多个 `<article data-page>`。每页 CSS 指定整数像素宽高（默认1080×1440），无 transform 缩放。无需 schema、节点字段或 readiness 回调。导出器按 DOM 顺序生成 `page-01.png` 等，DPR=1，像素尺寸与画布一致。

最终 HTML 自包含：SVG 内联，照片与自定义字体用获授权的 data URI 内嵌；系统中文字体可用，但跨机可能换行不同。`@font-face` 字体需要实际加载成功，输出 `report.json` 记录检查结果。按[字体加载](fonts.md)，导出器在布局检查前依次尝试 CDN、可选本地 WOFF2 和系统回退，成功字体及状态内嵌到成品。成品不依赖外部 CSS、SDK、字体 CDN 或页面脚本；不需要动画、滚动懒加载和交互。

导出器关闭页面 JavaScript、阻止页面发起的网络/外部文件子资源；字体获取由导出器单独处理，不开放任意页面外链。等待选定字体和图片解码后，检查空页、尺寸、DOM/SVG越界及文字盒的滚动溢出。自动检查覆盖不到所有叠压、裁切或字形缺失，必须查看实际 PNG。无需用栅格图片替代 SVG 文字以通过检查。

## 环境与命令

Python≥3.10，Python Playwright 与 Chromium/Chrome。已有依赖优先复用。宿主允许安装时在隔离环境执行 `python -m pip install -r requirements.txt` 与 `python -m playwright install chromium`；脚本不会安装依赖。已有浏览器传 `--browser /绝对路径/Chrome`。

```bash
python scripts/export.py --html /work/magazine.html --output /work/export-01
```

输出目录必须为空，避免旧截图伪装成新成果。成功后生成 `magazine.html`、逐页 PNG、`images.zip` 与 `report.json`；ZIP 只含独立图片。把 `sources.md`、穿搭的抠图 PNG 与原图对应记录，以及需要的 `post.md` 放在同目录。只需 HTML 时仍在浏览器看过版面，不必强制打包 PNG。

失败时返回非零，诊断写在 `report.json`；不要交付错误截图。修正 HTML 后导出到新目录。通常一轮完整检查、一轮针对性修正足够；若还有错误继续根据实际诊断修正，不反复全量试凑字号。缺少浏览器时保留 HTML 并说明 PNG 尚未导出。

## 内容图片检查

新闻、时序故事与编辑拼贴模板的 `data-image-policy="raster"` 图片位必须替换成实际获取或生成并内嵌的栅格图片，保留标记后导出；模板原始矢量占位会被拒绝。新增内容图也使用该标记。有事实依据的科普／数据示意或用户指定示意图可使用 `diagram`，装饰 SVG 无需标记；不得为绕过失败而修改标记或把几何占位转 PNG。详细检索、例外与视觉验收见[配图规则](imagery.md)。

## 人工验收

逐页看原尺寸与约375px宽预览：中文是否缺字、正文和配色标注是否清晰、主辅视觉是否有差异、是否存在无意义大空白、照片裁切与图注归属是否正确。对照成稿检查全部段落和来源，穿搭对照原图检查衣服、配件、抠图边缘和色板。配图按[正式素材验收](imagery.md)逐槽核对：技术通过不能证明素材已生成或占位已替换；带待补图的导出只能作为草稿。文件通过结构检查或透明检查通过，都不等于视觉与事实验收通过。
