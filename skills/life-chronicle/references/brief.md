# 人物志输入

共同字段：`title`、`subtitle`、`template`、`layout`、`events`、`sourceNote`、`sources`。`template` 选择构图，省略或填 `random` 时由脚本抽选；`layout` 选择 `landscape` 或 `portrait`，默认横版。两者独立，改变方向时重排，不拉伸画布。

```json
{
  "title": "人物名：一条人生主线",
  "subtitle": "概括人物经历与影响",
  "layout": "landscape",
  "template": "photo-wall-timeline",
  "portraitCutout": {"src": "assets/person.png", "alt": "真实人物肖像抠图", "outlineWidth": 6},
  "photoWall": [{
    "image": {"src": "assets/archive.jpg", "alt": "档案照片的主体与实际年代", "cropPosition": [0.5, 0.4]},
    "eventOrder": 1,
    "caption": "约1920年 · 工作场景"
  }],
  "events": [{
    "order": 1,
    "dateLabel": "约1920年",
    "title": "事件标题",
    "body": "这一事件的具体内容和意义"
  }],
  "sourceNote": "史料与摄影署名简称；完整出处见 sources.json",
  "sources": [{"eventOrder": 1, "url": "真实传记或档案链接", "datePrecision": "约年份", "imageCredit": "照片出处"}]
}
```

以上示意照片墙输入，需要2–8个事件、2–8张照片。照片 `eventOrder` 必填，绑定事件的 `order`；按事件排序后统一生成照片与时间线编号。`caption` ≤24字，默认采用事件标题；照片年代与事件不同，则显式填写实际年代与“资料照”。原始图片出处、拍摄年代、事件关联理由保存在 `sources` 中，不能只用不可见的出处说明纠正明显错配。

- `order` 为唯一数值，按真实先后排序；`dateLabel` ≤16字，保留约数、年代和区间，不补造精确日期。
- 照片墙、网格和照片环的事件标题≤10字，原生 Storyline≤7字。正文上限65字，实际容量随模板、方向和事件数变化；框内放不下会报错，不截字或缩小字号。
- `sourceNote` ≤95字；`sources` 记录史实与照片来源。输入图像均为 `{src,alt}` 本地素材，不引用会过期的工具返回地址。

## 随机选择与复用

- 先运行 `select_template.py --event-count N --output output/template-selection.json`，再读选中模板的指引并搜图、组织文案。4–8个事件在三个模板中等概率抽选，2–3个只在照片墙／照片环中抽选；原生 Storyline 不参与随机。
- `build.py --output output` 会复用该目录的抽选记录。未预先抽选则构建时抽选并保存，即使排版失败、需要修改文案也不重抽。同一作品复用目录，新作品用新目录。随机允许连续抽到相同模板。
- 用户指定构图时，填写明确的 `template`，它优先于旧记录。不要为绕开容量报错反复抽选；缩短文案或拆页。事件数变化使已选网格不再适用时，应重新规划。
- 构建时才随机的通用输入使用 `portraitCutout`＋每个 `events[].image`（含必要的 `imageCaption`，通用输入≤24字以兼容照片墙），不要混入模板专属 `photoWall`。已准备好的照片墙专属输入须显式填写 `photo-wall-timeline`。

## 照片墙＋时间线

`template: photo-wall-timeline`；横版1600×1000，竖版1080×1920，都按标题1/8、照片墙4/8、时间线3/8划分。`portraitCutout` 必填；`photoWall` 省略时从带 `image` 的事件收集照片。`monochrome` 默认 `true`，改为 `false` 保留彩色。排版与素材槽位见 [照片墙模板](photo-wall-timeline.md)。

## 中心网格

`template: center-grid`；竖版1080×1920，横版1920×1280。标题1/8，网格与来源7/8。需要4–8个事件，每项自带 `image: {src,alt}`，可用 `imageCaption`（≤40字）说明实际拍摄年代；不填写 `photoWall`。`portraitCutout`、`monochrome`、`accent` 与照片墙相同。中央剪贴画不编号，事件卡片按 `order` 排序编号。具体构图见 [网格模板](center-grid.md)。

## 环形叙事

`template: photo-ring`；竖版1200×1600，横版1600×1200。标题1/8、主体7/8。主体左边是按高度计算的照片半环，中央为描边人物，右边为引线连接的无底色文字卡片。需要2–8个事件，每项包含 `image: {src,alt}`，可填 `imageCaption`（≤40字）说明照片实际年代。`portraitCutout` 必填，不填写 `photoWall`；`monochrome` / `accent` 与前两种模板一致。见 [照片环模板](photo-ring.md)。

## 原生 Storyline（显式选择）

`template: storyline` 保留旧原生叙事流程，横版1600×1000、竖版1080×1920。`events[].image` 必填，映射为 `storyline.blocks`。完整日期进入可见 `content`；可选 `marker` ≤4字，省略取顺序号；`subImage` 为关联小图。`titleImage` 与 `backgroundImage` 为可选 `{src,alt}`，不使用 `portraitCutout` / `photoWall`。

所有模板 `title` ≤32字、`subtitle` ≤100字。旧竖版若要继续原生 Storyline，显式补 `template: storyline`；只写 `layout: portrait` 表示竖版，模板按随机规则选取。
