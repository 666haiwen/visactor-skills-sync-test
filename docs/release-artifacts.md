# Skills 发布产物接口 v1

GitHub 仓库是源码来源；下游平台负责上架、市场身份/版本映射和成功同步记录。本接口不包含平台凭证、空间配置或同步状态。

## 发布识别

- 仓库：`VisActor/skills`。
- 正式 tag：`skills-vMAJOR.MINOR.PATCH`，三个数值均为非负十进制整数，不允许前导零；没有既有正式格式 tag 或 Release 时，发布预检与正式发布都要求首个版本为 `skills-v1.0.0`。中断留下的 tag/草稿会保留该版本号，不允许覆盖。
- 下游只消费 GitHub Release 中 `draft=false`、`prerelease=false` 且 tag 符合上述规则的版本。当前发布工具不生成预发布版本；预发布后缀、旧 SDK 的 `v*` tag 均不属于本接口。
- 单独出现 tag 不代表发布完成。发布端先固定 tag 和创建草稿，上传并校验全部附件后才发布 Release。
- tag、已发布 manifest 和 ZIP 不移动、不复用、不覆盖。更正需要发布新版本。下游发现同一 tag 的 commit 或附件内容变化，应停止并报告。
- 发布正文读取同一提交中的 `docs/releases/<tag>.md`；预检展示完整正文，缺失或空文件会阻止发布。该维护文件不属于 Skill 包，也不影响 Skill 内容指纹。
- 发布前的预检与 CI 构建不创建 tag/Release；Actions 的 `skills-release-preview` 也不是正式发布源。

## 附件与包边界

每个 Release 都提供完整清单 `skills-manifest.json` 和清单内每个 Skill 的 `<name>.zip`，即使某个 Skill 与上个版本完全相同，也会在新 Release 中提供。下游自行根据上次成功记录选择更新项。

打包代码为 `.github/scripts/package_skills.py`，CI 与正式发布共同调用。输入是确定的 Git commit，内容读取 Git tree/blob，而非工作目录：

- 包含 `skills/<name>/` 下该提交中**全部已跟踪普通文件**；不维护另一套扩展名白名单或排除清单。`SKILL.md`、references、scripts、templates、assets、依赖声明都在范围内，目录内的 README 也属于发布内容。
- 不包含仓库级 tests、cases、examples、维护文档、未跟踪文件、忽略文件或未提交修改。`.gitignore` 不能排除已经提交的文件；不要将缓存提交到 Skill 目录。
- `name` 使用小写字母、数字和分隔用连字符，必须与目录和 `SKILL.md` frontmatter 的 `name` 一致；该字段使用普通字符串或带引号的同名字符串。
- Skill 必须自包含。没有隐式复制外部共享资源的规则；如未来引入共享资源，必须先明确纳入各自发布包并计入指纹。
- 只接受 Git 文件模式 `100644` / `100755`；符号链接和子模块会阻止构建。路径必须为 UTF-8 相对路径，禁止反斜杠、控制字符、冒号、空段、`.`、`..` 以及大小写冲突。
- ZIP 内直接放 `SKILL.md` 及其他相对路径，不额外嵌套 `<name>/` 目录。空目录不单独打包。
- ZIP 条目按路径的 UTF-8 字节序排序，使用 STORE（不压缩），时间统一为 `1980-01-01 00:00:00`，Unix 文件模式固定为原 Git 模式，保留原始文件字节；不写入 tag、commit、机器路径或生成时间。

## Manifest 字段

JSON 使用 UTF-8。以下为结构示意，尖括号内容是占位符；真实清单中的长度为非负整数，SHA-256 为 64 位小写十六进制字符串。

```json
{
  "schema_version": 1,
  "repository": "VisActor/skills",
  "tag": "skills-v1.0.0",
  "commit": "<完整 Git commit SHA>",
  "fingerprint_algorithm": "visactor-skill-content-v1",
  "skills": [
    {
      "name": "chart-storytelling",
      "path": "skills/chart-storytelling",
      "content_sha256": "<内容指纹>",
      "files": [
        {
          "path": "SKILL.md",
          "mode": "100644",
          "size": 123,
          "sha256": "<文件原始字节的 SHA-256>"
        }
      ],
      "package": {
        "asset": "chart-storytelling.zip",
        "size": 456,
        "sha256": "<整个 ZIP 文件的 SHA-256>"
      }
    }
  ]
}
```

`skills` 是该版本的完整库存，按名称排序；`files` 是包内完整文件清单，按相对路径 UTF-8 字节序排序。`size` 的单位为字节。`package.asset` 是同一 Release 下的附件名，不是本地路径或市场 Skill ID。

下载应通过该 Release 的 assets 列表，按附件名取 `browser_download_url`。同时核对 manifest 的 repository、tag、commit 与源仓库及 tag 实际指向的 commit 一致；不要用分支当前 HEAD 替代。消费者遇到未知 `schema_version` 或 `fingerprint_algorithm` 应停止，不能猜测兼容。

## 内容指纹的精确定义

算法标识：`visactor-skill-content-v1`。按文件相对路径的 UTF-8 字节序排序，拼接以下 UTF-8 字节串，最后计算 SHA-256：

```text
visactor-skill-content-v1\n
<mode>\t<sha256>\t<path>\n
<mode>\t<sha256>\t<path>\n
...
```

上面 `\n` 为单个 LF（`0a`），`\t` 为单个 TAB（`09`）；每一行包括最后一行都以 LF 结束，没有额外空行。`mode` 为原样六位 Git 模式字符串；`sha256` 为文件原始字节的 64 位小写十六进制摘要；`path` 为包根目录下的相对路径，分隔符为 `/`。不执行换行、Unicode 或文件内容归一化。

可直接复用的参考实现：

```python
import hashlib

records = "visactor-skill-content-v1\n" + "".join(
    f"{file['mode']}\t{file['sha256']}\t{file['path']}\n"
    for file in sorted(files, key=lambda file: file['path'].encode('utf-8'))
)
content_sha256 = hashlib.sha256(records.encode('utf-8')).hexdigest()
```

**增量判断使用 `content_sha256`；下载完整性使用 `package.sha256`。** 内容指纹不包含仓库 tag、commit、ZIP 元数据、发布时间或市场版本。因此仓库其他内容变更或仅发布新 tag，不会让未改动的 Skill 被误判为更新。文件新增、删除、改名、权限或内容变化都会影响指纹。

## 下游处理流程

1. 检测符合规则的已发布 Release，下载 manifest 并核对源 tag/commit；校验 manifest 附件的 GitHub asset `digest`（`sha256:<hex>`）。摘要用于传输完整性校验，不替代仓库访问控制或签名认证。
2. 以 `repository + skill.name` 为源码身份，将 `content_sha256` 与该 Skill **上次成功上架**记录比较；不要仅比较相邻 tag。失败项即使下次 tag 内容没变，也应继续被选中。
3. 对待发布项，从同一 Release 下载 `package.asset`。校验 ZIP 的大小、SHA-256、完整文件库存、逐文件大小/摘要/模式，并重算内容指纹。拒绝额外、缺失、重复或不安全路径，校验完成前不执行包内脚本。
4. 按下游 CLI 要求发布原包，或解压到隔离目录后发布。若平台需要版本元数据注入，由下游记录该适配及最终上传内容；不得改写 GitHub 源码/附件，不把市场版本注入后的包摘要误作源码指纹。
5. 仅在确认远端成功后推进该 Skill 的记录，至少保存源 tag、commit、内容指纹、包摘要、市场 Skill ID 和市场版本。结果不确定时先查询远端再决定重试。
6. 完整库存可识别新增与删除候选，但不能推断改名关系。改名/删除需显式确认身份映射和市场处置，不自动下架。自动同步不得因补处理旧 Release 而回滚已经成功发布的更新版本。

仓库不为各 Skill 增加独立版本字段。若平台接受 SemVer 且允许跳号，可将发生变化的 Skill 在 `skills-v1.2.0` 中发布为市场版本 `1.2.0`；未变化项保留原市场版本。该映射由平台约束决定，不属于 manifest 保证。

## 本地构建与验证

```bash
uv run --locked python .github/scripts/package_skills.py \
  --commit HEAD --tag skills-v1.0.0 --output .cache/release-preview
uv run --locked pytest tests/test_release.py tests/test_release_packages.py -q
```

输出目录必须不存在，避免混入旧文件。这里的 `--tag` 仅写入本地 manifest，**不会创建 Git tag 或 Release**。若要复现已发布版本，使用其准确 commit 和 tag。

本地测试覆盖包边界、跨 tag 稳定性、独立 Skill 增量、文件模式/路径/内容变更、ZIP 校验以及发布失败时保持草稿。真实 GitHub 上传与平台上架仍需在明确授权的正式试点中验证。
