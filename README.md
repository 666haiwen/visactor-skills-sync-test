# VisActor Skills

[English](README.md) | [简体中文](README.zh-CN.md)

Agent skills for the VisActor visualization ecosystem. Create data stories, editorial image series and biography posters with independently installable Skills. VChart and VTable Skills are maintained in their respective library repositories.

## Skills

| Skill | Tasks | Source |
| --- | --- | --- |
| [VChart Skill](https://github.com/VisActor/VChart/blob/develop/skills/vchart-development-assistant/SKILL.md) | Chart generation, diagnosis, image replication and React integration | [VisActor/VChart](https://github.com/VisActor/VChart) |
| [VTable Skill](https://github.com/VisActor/VTable/blob/develop/skills/vtable-development-assistant/SKILL.md) | List tables, pivot tables/charts, interactions and diagnosis | [VisActor/VTable](https://github.com/VisActor/VTable) |
| [data-storytelling](skills/data-storytelling/SKILL.md) | Data analysis, narrative design, scrollytelling, HTML reports and Web-PPT | This repository |
| [editorial-magazine](skills/editorial-magazine/SKILL.md) | Editorial HTML / PNG series for news, biographies, outfits, travel, chronological stories and explainers | This repository |
| [life-chronicle](skills/life-chronicle/SKILL.md) | Biography posters with photo walls, center grids, photo rings and editable timelines | This repository |

Each skill includes its instructions, local references, templates and scripts. No separate VisActor CLI, MCP server, model key or hosted VisActor API is required. The host agent supplies the model.

**Recommended: use the Skills directly in Codex or Claude Code.** Your agent provides model access and tool execution. Other compatible agents may also use these Skills, but do not have dedicated setup instructions here.

## Install

Run these commands in the project where you want to use the Skills:

```bash
npx skills add VisActor/VChart --skill vchart-development-assistant
npx skills add VisActor/VTable --skill vtable-development-assistant
npx skills add VisActor/skills --skill data-storytelling
npx skills add VisActor/skills --skill editorial-magazine
npx skills add VisActor/skills --skill life-chronicle
```

Follow the installer's prompts to select Codex or Claude Code. You can install each Skill independently. More installation options are documented in the [Skills CLI reference](https://github.com/vercel-labs/skills#usage).

Requirements:

- Node.js and npm to run the installation commands above.
- An agent with filesystem and shell tools, plus its own model access.
- Python 3.10+ and Node.js (JavaScript validation) for data-storytelling. Python scripts use the standard library. See the upstream repositories for VChart/VTable Skill requirements.
- A browser and internet access for generated HTML. Data-storytelling loads pinned VSeed, VChart, VTable and GSAP packages from the public unpkg CDN.

Editorial magazines and biography posters additionally require Python 3.10+, Pillow, Playwright and Chromium/Chrome; install the selected Skill's `requirements.txt`. Fonts load from a Feishu CDN mirror with system fallbacks. Life Chronicle also loads a pinned VInfo SDK; see its [environment guide](skills/life-chronicle/references/environment.md). Image search, generation and cutout tools come from the host. Magazine templates contain placeholders that must be replaced for delivery.

## Use

After installation, ask your agent to use the selected Skill with your data. For example:

- “Use VChart to compare sales by region and quarter in this CSV. Give me the editable source and HTML.”
- “Use VTable to build a sortable detail table using every row in this file.”
- “Use data-storytelling to explain retention changes in this CSV to our growth lead as a shareable HTML story.”

Data-storytelling uses the current agent to author VSeed configurations and local scripts to assemble the output; it needs no hosted chart generation service. Images use host capabilities or the declared fallback. Web-PPT is a browser presentation, not a `.pptx` file.

Generated JavaScript/HTML is executable code. Preview your own or reviewed artifacts locally; the evaluation browser is not a sandbox for arbitrary untrusted submissions.

## Development and maintenance

This section is for contributors editing Skills or running local tests. The default and primary maintenance branch is `develop`. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

### Install from a local checkout

From the root of your local repository, install the working copy of a Skill:

```bash
npx skills add ./skills/data-storytelling
npx skills add ./skills/editorial-magazine
npx skills add ./skills/life-chronicle
```

Alternatively, copy the complete Skill directory into your agent's skill directory, including its references, templates and scripts. Do not copy only `SKILL.md`. See the [local debugging guide](docs/debugging.md) for Codex and Claude Code workspace setup. Refresh the installed copy after changing a Skill before retesting.

### Regression tests

The Python maintenance environment requires Python 3.12+ and [uv](https://docs.astral.sh/uv/):

```bash
uv sync --locked
uv run pytest tests -q
uv run ruff check skills tests evals/scripts
```

Fixed browser smoke cases are maintained by Skill in [evals/smoke/](evals/smoke/README.md), with each case's configuration, inputs and acceptance criteria together. Run all with `uv run python evals/scripts/smoke.py`, or select `--skill data-storytelling` / `--case story-ppt` after the browser setup in that guide.

### Model API task debugging

A lightweight harness can load this repository's Skill through OpenAI-compatible Chat Completions, run fixed or custom tasks, and retain request, tool, usage and artifact logs. Use it for bounded script/task debugging; end-to-end data storytelling is recommended in Codex or Claude Code.

See the [evaluation guide](evals/README.md) for setup and commands. The [case catalog](evals/cases/README.md) contains five data-storytelling tasks; browser smoke covers HTML stories and Web-PPT. Model tasks are excluded from CI and may incur provider charges.

## Versioning

Skills maintained here are versioned together at repository level. Each formal Skills release is identified by a Git tag covering the Skill instructions, references, templates and scripts. VChart and VTable Skill versions are managed by their respective repositories.

Use a release tag or commit SHA to identify the version when reporting an issue or reproducing a result; branch contents can change. Dependency versions such as VTable `1.26.8` identify the underlying library, not the Skill release. Historical VMind SDK tags remain unchanged and belong to the earlier SDK.

## Earlier VMind versions

The previous VMind SDK is no longer maintained. Its code and documentation remain in [historical releases](https://github.com/VisActor/skills/releases).

[MIT license](LICENSE)
