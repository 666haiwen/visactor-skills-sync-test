# Browser smoke tests

[English](README.md) | [简体中文](README.zh-CN.md)

Use fixed inputs to check Skill scripts, templates and generated pages. These tests run locally and in CI without calling a model.

## What is tested

| Skill | Case | Checks |
| --- | --- | --- |
| data-storytelling | [story-html](data-storytelling/story-html) | Assemble an HTML story and render its chart |
| data-storytelling | [story-ppt](data-storytelling/story-ppt) | Assemble a Web-PPT, render its chart and navigate forward and back |

Both cases check for a nonblank chart canvas, page/resource errors and successful local asset loading. PPT navigation checks the target slide's position and visibility. Smoke uses reduced motion and does not assess animation or narrative quality. Screenshots are diagnostic evidence, not pixel-comparison targets.

## Run

From the repository root:

```bash
uv sync --locked
npm ci --prefix evals --ignore-scripts
node evals/node_modules/playwright/cli.js install chromium

uv run python evals/scripts/smoke.py
uv run python evals/scripts/smoke.py --skill data-storytelling
uv run python evals/scripts/smoke.py --case story-ppt
```

On Linux, use `install --with-deps chromium` if browser system libraries are missing.

Reports, logs, inputs, generated files and screenshots are saved under `.cache/`. Use `--output-dir PATH` to select a new output directory. Any failed case produces a nonzero exit code.

## Case files

Each `<skill>/<case>/` directory contains `config.json` (build settings), `inputs/` (fixed inputs) and `expectations.json` (required checks). Add cases under the corresponding Skill directory; the runner discovers them automatically.
