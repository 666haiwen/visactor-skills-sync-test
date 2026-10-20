# Contributing

Changes to Skills should protect a concrete user task or failure mode. Keep runtime instructions/resources under `skills/`, deterministic regressions under `tests/`, and fixed Agent tasks under `evals/`.

## Start here

Use `develop` as the default and primary maintenance branch. Create contribution branches from the latest `origin/develop` and target pull requests to `develop`.

VChart and VTable Skills are maintained in [VisActor/VChart](https://github.com/VisActor/VChart/tree/develop/skills/vchart-development-assistant) and [VisActor/VTable](https://github.com/VisActor/VTable/tree/develop/skills/vtable-development-assistant). Make changes to those Skills in their owning repositories.

The recommended development loop is [direct Skill debugging in Codex or Claude Code](docs/debugging.md). Use their existing harness for exploration and iterative fixes. The API harness is a lightweight alternative for fixed cases or a custom prompt with input files; it supports only OpenAI-compatible Chat Completions.

1. Pick the Skill and reproduce the task in Codex or Claude Code. See [local debugging](docs/debugging.md) for setup; use your own prompt/assets or an existing fixed case.
2. Run `uv sync --locked`, then select the relevant regressions below. These checks need no model account.
3. Inspect the generated source, screenshots and required interactions. Record the prompt, inputs, host/model and observed result. Automated success does not replace semantic or visual review.
4. For Python changes, run Ruff on the affected paths. Broaden verification when shared tooling or multiple Skills are affected.

### Adding or updating a Skill

- Use `skills/<skill-name>/SKILL.md` with a lowercase hyphenated directory name matching the frontmatter `name`. Keep required references, assets, templates, scripts and optional dependency declarations in that directory.
- Skills must work when copied independently. Do not import maintenance files or resources from a sibling Skill directory. Keep tests, evaluation cases and generated artifacts outside the installed Skill.
- Put Skill-specific Python tests in `tests/<skill_name>/`, replacing hyphens with underscores. Keep shared runner, installation and browser infrastructure tests at the test root. Node.js integrations currently also live there.
- Curated user-facing examples belong in `examples/<skill-name>/<case-name>/`; follow the [example guide](examples/README.md) for prompts, inputs, final artifacts, previews and usage instructions. Review outputs before showcasing them; keep raw execution logs local.
- Model tasks belong in `evals/cases/<skill-name>/`; browser cases belong in `evals/smoke/<skill-name>/<case-id>/`. Add meaningful cases for stable behavior when appropriate; do not create empty catalogs just to mirror every installed Skill. Runtime discovery and fixed-case coverage are separate.
- Update both root READMEs with the Skill's tasks, install command and requirements. If a task needs a new harness or browser adapter, implement and verify it before documenting support. Do not relax the existing tool allowlist merely to make a new Skill appear supported.

### Select checks by scope

| Scope | Deterministic regressions | Fixed model/browser coverage |
| --- | --- | --- |
| data-storytelling | `uv run pytest tests/data_storytelling -q`; `node --test tests/test_story_vseed.cjs` after `npm ci --prefix evals --ignore-scripts` | [Model tasks](evals/cases/data-storytelling/README.md); HTML and Web-PPT smoke |
| editorial-magazine | `uv run pytest tests/editorial_magazine -q` | No fixed model tasks or browser smoke yet; inspect outputs with a full agent |
| life-chronicle | `uv run pytest tests/life_chronicle -q` | No fixed model tasks or browser smoke yet; inspect outputs with a full agent |
| Packaging | `uv run pytest tests/test_portable_install.py -q` | Copied Skill execution without the source checkout |
| Shared evaluation tooling | Relevant root tests, or `uv run pytest tests -q` for changes across modules | See the [smoke guide](evals/smoke/README.md) for browser setup |

For example, lint `skills/life-chronicle tests/life_chronicle` when changing its Python helpers. Use `uv run ruff check skills tests evals/scripts` for changes spanning Skills or shared tooling. CI runs the full deterministic suite.

The optional API runner copies only the selected Skill into a fresh case workspace. It provides file/image tools and allowlisted data-storytelling scripts; editorial-magazine and life-chronicle have no script adapters. For bounded API investigations, follow the [API quickstart](evals/README.md#contributor-quickstart), start with one task and inspect `usage.json`. For full workflows, use Codex or Claude Code. `--runner codex` can run fixed or custom tasks through that host; it does not make the API harness equivalent to a coding agent.

## Continuous integration

`Skills CI` runs on pull requests and pushes to `main`/`develop`, with two jobs:

- **Lint and regressions**: install locked Python dependencies, run Ruff and the deterministic test suite, including per-Skill case/input contracts and a simulated model API.
- **Browser smoke (no model)**: use copied Skills to generate a fixed HTML data story and Web-PPT deck, then check chart rendering, slide navigation and browser errors. Pinned npm packages serve CDN requests locally; unexpected external requests fail. Save JSON reports, logs, generated HTML and screenshots for seven days.

Maintain browser smoke configurations, inputs and acceptance criteria together under `evals/smoke/<skill-name>/<case-id>/`. The runner discovers them automatically; see the [smoke case guide](evals/smoke/README.md) for the catalog, file contract and adding cases.

Neither job calls a model or needs model credentials. Browser smoke checks script/template integration, not Skill quality on model-generated tasks. Model evaluation remains a separate local development activity.

To run browser smoke locally:

```bash
npm ci --prefix evals --ignore-scripts
node evals/node_modules/playwright/cli.js install chromium
node --test tests/test_browser_assets.mjs tests/test_browser_checks.mjs tests/test_story_vseed.cjs
uv run python evals/scripts/smoke.py
# Select a Skill or a single fixed browser case
uv run python evals/scripts/smoke.py --skill data-storytelling
uv run python evals/scripts/smoke.py --case story-ppt
```

On Linux, use `install --with-deps chromium` when system libraries are missing. Each run creates a new evidence directory under `.cache/`; `--output-dir PATH` selects an explicit directory that must not exist yet.

## Before committing

Enable the repository's Git hooks after cloning or switching from the historical SDK checkout:

```bash
git config core.hooksPath .githooks
```

The hooks check staged whitespace, run Ruff for Python/tooling changes and require a Conventional Commit subject. Python checks require `uv` on PATH. Run the relevant tests before committing; the hook does not run model evaluations or the complete test suite. These hooks replace the historical Rush hooks, whose scripts are no longer part of this repository.

Explain the task or defect, the behavior changed, and why the chosen cases protect it. Include the commands, case ids, Agent version, requested model and review outcomes. Report known failures and skipped checks. An exit code of zero means the automated checks passed, not that every rendered artifact is correct.

Add cases for distinct behaviors or meaningful regressions, not just to increase the count. Keep prompts and inputs separate from expectations; use public or synthetic fixtures and record provenance. Keep `evals/runs/`, credentials and private data out of commits. Runtime Skills must work independently of maintenance tools and the historical VMind SDK.
