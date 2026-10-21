# Contributing

Changes to Skills should protect a concrete user task or failure mode. Keep runtime instructions/resources under `skills/`, deterministic regressions under `tests/`, fixed Agent tasks under `cases/`, and curated results under `examples/`.

## Start here

Use `main` as the default, user-facing stable branch and `develop` for day-to-day maintenance. Publish reviewed updates through a `develop` → `main` pull request. Create contribution branches from the latest `origin/develop` and target pull requests to `develop`.

VChart and VTable Skills are maintained in [VisActor/VChart](https://github.com/VisActor/VChart/tree/develop/skills/vchart-development-assistant) and [VisActor/VTable](https://github.com/VisActor/VTable/tree/develop/skills/vtable-development-assistant). Make changes to those Skills in their owning repositories.

1. Reproduce a task with a mature agent such as Codex or Claude Code. Follow [local debugging](docs/debugging.md) to create an ignored `.cache/skill-dev/<skill-name>/<run-name>/` workspace. Use your own prompt/assets or a [fixed task](cases/README.md).
2. Edit the Skill source, refresh the installed copy and retest. Inspect generated files and required interactions. Keep the prompt, inputs, host/model, available logs and screenshots locally; automated success does not replace semantic or visual review.
3. Run `uv sync --locked`, then the relevant regressions below. These checks need no model account.
4. For Python changes, run Ruff on the affected paths. Broaden verification when shared tooling or multiple Skills are affected.

### Adding or updating a Skill

- Use `skills/<skill-name>/SKILL.md` with a lowercase hyphenated directory matching the frontmatter `name`. Keep required references, assets, templates, scripts and optional dependency declarations in that directory.
- Skills must work when copied independently. Do not import maintenance files or resources from a sibling Skill. Keep tests, task cases and generated artifacts outside the installed Skill.
- Put Skill-specific Python regressions in `tests/<skill_name>/`, replacing hyphens with underscores. Shared installation/tooling tests and Node.js integrations live at the test root.
- Fixed Agent tasks belong in `cases/<skill-name>/<case-name>/`, with prompt, inputs and acceptance guidance together. Follow the [case guide](cases/README.md). Keep reviewer criteria outside the generation workspace; allow different correct outputs.
- Fixed browser cases belong in `tests/browser/cases/<skill-name>/<case-id>/`. Configuration, inputs and expectations stay together; scripts and locked browser dependencies live under `tests/browser/`.
- Curated user-facing examples belong in `examples/<skill-name>/<case-name>/`; follow the [example guide](examples/README.md). Review outputs before showcasing them; keep raw execution logs local.
- Update both root READMEs with the Skill's tasks, install command and requirements. Document actual test coverage; do not create empty catalogs just to mirror every installed Skill.

### Select checks by scope

| Scope | Deterministic regressions | Task/browser coverage |
| --- | --- | --- |
| data-storytelling | `uv run pytest tests/data_storytelling -q`; `node --test tests/test_story_vseed.cjs` after browser dependency installation | [Fixed tasks](cases/README.md); HTML and Web-PPT smoke |
| editorial-magazine | `uv run pytest tests/editorial_magazine -q` | No fixed tasks or browser smoke yet; inspect outputs with an agent |
| life-chronicle | `uv run pytest tests/life_chronicle -q` | No fixed tasks or browser smoke yet; inspect outputs with an agent |
| Packaging | `uv run pytest tests/test_portable_install.py -q` | Copied Skill execution without the source checkout |
| Shared test tooling | Relevant root tests, or `uv run pytest tests -q` for changes across modules | [Browser smoke guide](tests/browser/cases/README.md) |

For example, lint `skills/life-chronicle tests/life_chronicle` when changing its Python helpers. Use `uv run ruff check skills tests` for changes spanning Skills or shared tooling. CI runs the full deterministic suite.

## Continuous integration

`Skills CI` runs on pull requests and pushes to `main`/`develop`, with two jobs:

- **Lint and regressions**: install locked Python dependencies, run Ruff and deterministic tests, including copied Skill execution and fixed-input integrity checks.
- **Browser smoke (no model)**: use copied Skills to generate a fixed HTML story and Web-PPT, then check chart rendering, slide navigation and browser errors. Pinned npm packages serve CDN requests locally; unexpected external requests fail. Save JSON reports, logs, generated HTML and screenshots for seven days.

Neither job calls a model or needs model credentials. Browser smoke checks script/template integration. Execute fixed Agent tasks locally and review their results separately.

To run browser checks locally:

```bash
npm ci --prefix tests/browser --ignore-scripts
node tests/browser/node_modules/playwright/cli.js install chromium
node --test tests/test_browser_assets.mjs tests/test_browser_checks.mjs tests/test_story_vseed.cjs
uv run python tests/browser/scripts/smoke.py
# Select a Skill or a single fixed browser case
uv run python tests/browser/scripts/smoke.py --skill data-storytelling
uv run python tests/browser/scripts/smoke.py --case story-ppt
```

On Linux, use `install --with-deps chromium` when system libraries are missing. Each smoke run creates a new evidence directory under `.cache/`; `--output-dir PATH` selects an explicit directory that must not exist yet.

## Before committing

Enable repository hooks:

```bash
git config core.hooksPath .githooks
```

Hooks check staged whitespace, run Ruff for Python/tooling changes and require a Conventional Commit subject. Python checks require `uv` on PATH. Run relevant tests before committing; hooks do not run model tasks or the complete test suite.

Explain the task or defect, the behavior changed and why the selected checks protect it. Include commands, case ids and review outcomes; for agent runs, include the host/model and Skill revision. Report failures and skipped checks. Add cases for distinct behaviors, not just to increase the count. Keep credentials, private data and raw execution evidence out of commits.
