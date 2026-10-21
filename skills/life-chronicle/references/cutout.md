# 人物剪贴画：统一透明 PNG

布局只接收 `portraitCutout: {src, alt}`，不关心是哪种工具完成抠图。`src` 为已下载的本地透明 PNG；照片原件、摄影署名、实际拍摄年代和加工记录留在来源清单。主像不能遮挡标题、照片外侧编号或时间线。

白色外轮廓由版式合成统一添加，默认6px，可用 `portraitCutout.outlineWidth` 调整或设0关闭。本地脚本与 MediaKit 都只需提供干净的透明人物，无需预先加描边，避免重复处理。

## 本地脚本

单人、身体轮廓清楚的原照更适合抠图。可选依赖为 `requirements-cutout.txt`（rembg CPU）；不会随基础渲染强制安装。已有透明图只需 Pillow。

```bash
# 在允许安装依赖的隔离环境中安装一次
python -m pip install -r requirements-cutout.txt
# 首次下载公开模型需要显式开关；后续移除 --allow-model-download
python scripts/cutout.py --input portrait.jpg --output assets/person.png \
  --backend rembg --model-dir /可写缓存目录 \
  --model u2netp --allow-model-download
```

`u2netp` 是轻量起点；效果不足时可用已准备好的 `u2net` / `u2net_human_seg` 模型重新处理，或改用宿主 MediaKit。脚本不上传照片，不自动安装依赖；模型缓存由参数指定。模型与处理记录不打入 Skill 包。

输出 PNG 和同名 `.processing.json`，记录方法、模型、输入输出散列与尺寸。脚本检查可见前景与透明背景、去除空边、保留 alpha；仍须人工查看头发、脸、手和衣服边缘，不能用“带 alpha 通道”代替视觉验收。主体残缺时换图或换抠图方法，不生成替代面孔。

## 豆包 `byted-mediakit-image`

Skill 是操作指导，先发现并读取宿主实际安装的 `byted-mediakit-shared`、`byted-mediakit-image` 及背景移除 reference，再确认实时 CLI schema；不要假设存在 `call_skill()`。

已核对的 [MediaKit 镜像入口](https://github.com/ahang1598/doubao-workbuddy-qwenwork-skills/blob/e7fa55c063526c3ad3f7f8e10fa039516178049b/doubao/skills/byted-mediakit-image/SKILL.md) 使用：

```bash
mediakit-cli image remove-image-background --schema
mediakit-cli image remove-image-background --image-url "$PORTRAIT_INPUT" --scene human --output-format png
```

输入路径支持、鉴权和返回结构以宿主实时合同为准；本地文件可能经 Cloud 适配器上传。沿用用户对素材处理的授权和宿主鉴权。镜像记录的返回 `image_url` 为24小时下载链接，及时保存到本地，再归一化：

```bash
python scripts/cutout.py --input downloaded.png --output assets/person.png \
  --backend alpha --provider byted-mediakit-image
```

`--provider` 只记录来源，不负责调用豆包。MediaKit 和本地脚本最终使用同一 `portraitCutout` 字段，无需修改模板。宿主能力不可用时走本地脚本；两者均失败时明确素材缺口，不把矩形原照冒充已抠图素材。
