# Las Vegas GP：爆款成立，但转化不均

一套中文 Web-PPT，用霓虹视觉、图表、章节转场和逐步展开的证据，讨论城市体育事件的声量、收入结构与商业转化。包含 14 张幻灯片及一段分步图表场景。

**本案例使用模拟演示数据，不是真实赛事财务或运营结果。**

![案例预览](preview.png)

- [测试 Prompt](prompt.md)
- [最终 HTML](result/index.html)
- [图表幻灯片预览](result/chart-preview.png)
- [模拟输入数据](inputs/las-vegas-gp-mock.csv)

## 输入与使用

CSV 以 `dataset`、`row_id`、`record_json` 保存多个模拟数据表，共 3117 条记录。

在安装 chart-storytelling 的 Agent 中附上这个 CSV 与 `prompt.md`，要求输出 Web-PPT，采用 feature 视觉叙事模式。模拟数据只用于展示与调试，生成内容应继续说明数据性质。

用方向键或页面导航控件翻页；其中的分步图表场景会先推进内部步骤，再进入下一张。Web-PPT 是网页演示稿，不是 `.pptx`。

## 预览

在本案例目录执行：

```bash
uv run python -m http.server 8000
```

打开 <http://localhost:8000/result/index.html>。HTML 内嵌图片与绘图数据，仍需联网加载公开 CDN 上的固定版本脚本，无法完全离线运行。
