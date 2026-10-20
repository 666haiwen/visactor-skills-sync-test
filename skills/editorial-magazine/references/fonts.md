# 字体：按需加载，导出前固定

模板正文优先 `"Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif`，宋体标题或杂志长文优先 `"Noto Serif SC","Songti SC","SimSun",serif`。保留模板的衬线／无衬线分工与系统回退，不把所有文字换成一种字体。旅行正文默认300，栏目标题与重要交通时间可保留400–500。

## 默认导出链路

`scripts/export.py` 自动调用同目录 `font_loading.py`，只处理页面实际声明为首选的 Noto Sans SC／Noto Serif SC：

1. 从 `[data-page]` 内文本节点的计算样式收集字符、字重和字体，包含 HTML 与 SVG 文本。按实际需要向飞书 `https://miaoda.feishu.cn/fonts/css2` 请求字体样式；使用现代浏览器标识获取 WOFF2 分段，不假定所有请求都返回相同格式。
2. 只下载与实际字符、字重相交的字体分段；等待 `document.fonts.load()` 成功后才检查布局和截图。CDN 阶段所有字体共用20秒期限，超时或失败依次尝试可选本地 WOFF2、系统字体栈。
3. CDN 文件先下载再以 data URI 安装，不把远程 stylesheet 留在文档中。安装失败时移除临时样式及字体对象，避免迟到字体改变排版。成功字体与许可说明内嵌进交付 HTML，重开不再依赖 CDN；整页仍是无脚本的静态 HTML。
4. `report.json` 的 `fontResolution` 记录 family、weights、glyphCount、status、source 和失败原因；同一记录写入 HTML 的 `magazine-font-status` 元数据，渲染期间也可读 `window.__MAGAZINE_FONTS__`。发生系统回退时在交付说明中如实告知，不把 CSS 中写了字体名等同于加载成功。

字体二进制不随 skill 打包，只有本次实际用到的字体进入成品。CDN 可达性取决于运行环境，不能承诺内网一定可用。系统字体在不同机器上可能不同；回退后仍需查看换行、正文密度和边界。模板源码直接打开会先使用系统栈，正式结果以导出目录里的 `magazine.html` 为准。

```bash
# 默认：CDN → 可选本地 WOFF2 → 系统字体
python scripts/export.py --html /作品.html --output /新输出目录
# 离线环境：跳过 CDN，先检查本地字体
python scripts/export.py --html /作品.html --output /新输出目录 --font-mode offline
# 明确只使用已有内嵌字体及系统字体
python scripts/export.py --html /作品.html --output /新输出目录 --font-mode system
```

## 可选本地 WOFF2

默认读取本 skill 的 `assets/fonts.json`；也可用 `--font-assets /本次字体目录` 指定包外目录，避免把大字体加回分发包。没有 manifest 时正常走系统回退，无需创建空文件。

```json
[
  {
    "family": "Noto Sans SC",
    "weight": "300",
    "style": "normal",
    "file": "NotoSansSC-Light.woff2",
    "licenseFile": "OFL.txt"
  }
]
```

文件和许可都必须位于该字体目录内，包含符号链接解析后的路径；只接受实际 WOFF2 文件。真实可变字体可声明 `"weight":"100 900"`，静态字体按实际字重逐项配置，不把400文件标成300来伪造轻字重。支持可选 `unicodeRange` 分段声明；覆盖所需字重后仍通过浏览器解码检查。许可文本随 HTML 保留。Noto 的公开 OFL 文本见资源中的对应 `NotoSansSC-OFL.txt`、`NotoSerifSC-OFL.txt`。

用户指定其他字体时保留其选择，使用已有授权的内嵌 `@font-face` 或系统栈；本加载器不把未知字体映射到 Noto，也不自动搜索并下载任意字体。
