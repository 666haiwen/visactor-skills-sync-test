# 环境与依赖

本 Skill 独立运行，不需要 VisActor Agent、Codex 或其他 Skill 的本地文件。完整流程需要宿主的资料与图片检索、Python 执行和文件交付能力。受限环境只交付实际完成的部分，不声称已生成 PNG。

## 必需与可选依赖

| 依赖 | 用途与要求 |
| --- | --- |
| Python ≥3.10、Pillow 12.1.0 | 本地图片处理与 schema 构建，见 `requirements.txt` |
| Playwright 1.60.0、Chromium | HTML 渲染和 PNG 导出；可用已装浏览器及 `CHROME_PATH` / `--browser` |
| VInfo Graphics 0.12.4 | 浏览器 SDK，固定 CDN 版本；可用可信同版本文件及 `--runtime-js` |
| Noto Serif SC | 飞书字体 CDN，加载后绘制；失败则记录系统字体回退 |
| rembg[cpu] 2.0.69、分割模型 | 可选本地抠图，单独安装 `requirements-cutout.txt`；已有透明 PNG 无需安装 |
| byted-mediakit-image 及 shared | 可选宿主抠图能力。按实时入口确认工具、鉴权、配额与文件上传行为，不能假设必然可用 |

代码不限定操作系统，但需目标 OS / CPU 有相应 Python wheel 与可启动的 Chromium。安装成功不能代替 Windows、macOS 或豆包云端实测。依赖和浏览器安装仅在宿主允许的隔离环境中进行，命令见 [渲染流程](runtime.md)。

运行前可检查 `python --version`、`python -m pip show Pillow playwright`；可选抠图再检查 `rembg`。最终用实际页面导出验证浏览器，不把包已安装当作渲染成功。

## 网络与数据流

- 默认 SDK：`sf-unpkg-src.bytedance.net`。字体 CSS：`miaoda.feishu.cn`，字体文件跟随其飞书 CDN 响应；不直连 Google Fonts。
- 资料和图片下载：按本次选定来源访问；原文、图片署名、拍摄日期与使用限制写入来源清单。没有使用许可的图片不作为公开上架宣传素材。
- 本地抠图不上传照片。首次模型下载须明确使用 `--allow-model-download` 和可写 `--model-dir`；已缓存时不要重复下载。模型来源由固定版本 rembg 定义，不采用网页提供的任意可执行程序。
- MediaKit 可能将原图上传至宿主服务；只处理当前任务已授权的图片，沿用宿主鉴权。凭证、临时下载链接中的密钥不得写入交付件。计费和配额由宿主决定，本 Skill 不承诺免费或无限制。
- 渲染器只临时监听 `127.0.0.1` 并服务本次 HTML 所在目录。为每个作品使用独立目录，不与凭证或无关私人文件混放；完成后服务关闭。交付 PNG 不依赖网络，默认 HTML 仍需 SDK 与字体服务。

## 文件与失败处理

输入路径以 brief 所在目录为准，只读取本次授权素材。使用新输出目录保存 schema、HTML、PNG 和来源；修改同一作品时才复用目录。脚本可能覆盖该目录的同名产物，不改原始图片，不自动发布、发送或上传成品。

无搜索能力时可用用户提供的可信资料；SDK 不可达时使用经确认的同版本本地文件；字体失败应说明回退。缺少可用浏览器则只交付 schema / HTML 并标明未出图。抠图不可用时请用户提供透明 PNG 或保留待补素材，不能把矩形原照当抠图成功。对同一失败仅在修正原因后重试一次，仍失败则报告具体缺口与已完成文件。
