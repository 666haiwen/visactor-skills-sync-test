# 碳排放没有停下，地球还在继续升温

一篇面向大众读者的中文滚动数据故事，通过全球排放、能源结构、当期与累计责任等视角组织气候议题。展示数据叙事、滚动图表和暗色视觉表达。

![案例预览](preview.png)

- [测试 Prompt](prompt.md)
- [最终 HTML](result/index.html)
- [图表片段预览](result/chart-preview.png)
- [输入数据摘录](inputs/global-co2-excerpt.csv)

## 输入与复现边界

数据来源为 [Our World in Data CO₂ 数据集](https://github.com/owid/co2-data)。随案例保存的 CSV 只有 16 列、1300 行，不包含页面使用的 `temperature_change_from_co2`，也不是完整全球历史快照。

因此，这份摘录不足以完整重新生成该作品。HTML 已内嵌实际绘图数据，可以直接查看结果；测试同类任务时，应自行准备包含全球排放与温升归因字段的完整数据快照，并记录版本。温升归因不等于某国本地气温或某次极端天气的直接成因。

在安装 data-storytelling 的 Agent 中提供数据与 `prompt.md`，选择 HTML 滚动故事。

## 预览

在本案例目录执行：

```bash
uv run python -m http.server 8000
```

打开 <http://localhost:8000/result/index.html>。HTML 内嵌图片与绘图数据，仍需联网加载公开 CDN 上的固定版本脚本，无法完全离线运行。
