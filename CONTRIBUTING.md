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
| chart-storytelling | `uv run pytest tests/chart_storytelling -q`; `node --test tests/test_story_vseed.cjs` after browser dependency installation | [Fixed tasks](cases/README.md); HTML and Web-PPT smoke |
| editorial-magazine | `uv run pytest tests/editorial_magazine -q` | No fixed tasks or browser smoke yet; inspect outputs with an agent |
| life-chronicle | `uv run pytest tests/life_chronicle -q` | No fixed tasks or browser smoke yet; inspect outputs with an agent |
| Packaging | `uv run pytest tests/test_portable_install.py -q` | Copied Skill execution without the source checkout |
| Shared test tooling | Relevant root tests, or `uv run pytest tests -q` for changes across modules | [Browser smoke guide](tests/browser/cases/README.md) |
| Release tooling | `uv run pytest tests/test_release.py tests/test_release_packages.py -q`; `uv run ruff check .github/scripts tests/test_release.py tests/test_release_packages.py` | Mocked GitHub API; no tags or Releases are created |

For example, lint `skills/life-chronicle tests/life_chronicle` when changing its Python helpers. Use `uv run ruff check skills tests` for changes spanning Skills or shared tooling. CI runs the full deterministic suite.

## Continuous integration

`Skills CI` runs on pull requests and pushes to `main`/`develop`, with two jobs:

- **Lint and regressions**: install locked Python dependencies, run Ruff and deterministic tests, including copied Skill execution and fixed-input integrity checks. Build and verify release ZIPs/manifest from the checked-out Git commit using the same packager as publication; the CI-only label `skills-v0.0.0` creates no tag or Release.
- **Browser smoke (no model)**: use copied Skills to generate a fixed HTML story and Web-PPT, then check chart rendering, slide navigation and browser errors. Pinned npm packages serve CDN requests locally; unexpected external requests fail. Save JSON reports, logs, generated HTML and screenshots for seven days.

Neither job calls a model or needs model credentials. Browser smoke checks script/template integration. Execute fixed Agent tasks locally and review their results separately.

To run browser checks locally:

```bash
npm ci --prefix tests/browser --ignore-scripts
node tests/browser/node_modules/playwright/cli.js install chromium
node --test tests/test_browser_assets.mjs tests/test_browser_checks.mjs tests/test_story_vseed.cjs
uv run python tests/browser/scripts/smoke.py
# Select a Skill or a single fixed browser case
uv run python tests/browser/scripts/smoke.py --skill chart-storytelling
uv run python tests/browser/scripts/smoke.py --case story-ppt
```

On Linux, use `install --with-deps chromium` when system libraries are missing. Each smoke run creates a new evidence directory under `.cache/`; `--output-dir PATH` selects an explicit directory that must not exist yet.

## Publishing Skills

Maintainers decide when to release; GitHub Actions executes publication. A merge into `main` does not automatically create a tag or Release. Default-branch installations can receive changes as soon as they reach `main`; use a release tag or commit SHA when a fixed snapshot is required.

Version all maintained Skills together using `skills-vMAJOR.MINOR.PATCH`, starting at `skills-v1.0.0`:

| Change | Version increment |
| --- | --- |
| Compatible fixes to Skill instructions, scripts or templates | Patch, e.g. `skills-v1.0.1` |
| New Skills or compatible capabilities | Minor, e.g. `skills-v1.1.0` |
| Skill removals, renames or incompatible usage changes | Major, e.g. `skills-v2.0.0` |
| Documentation, showcase or maintenance-only changes | May merge without an immediate release |

When no stable Skills tag or Release exists, both preflight and publication require exactly `skills-v1.0.0`. A tag or draft left by an interrupted attempt reserves that version: inspect and complete it, or explicitly choose a higher version; never reuse it. The packager-only CI label `skills-v0.0.0` is not a publishable first version.

Historical VMind SDK `v*` tags remain unchanged and do not participate in Skills version ordering. This workflow publishes stable releases only; prerelease/build suffixes are not accepted. The Python project version is maintenance-tool metadata, not the Skills release version.

### Release procedure

1. Open a `develop` → `main` PR. Fill in the PR template's release plan: whether to publish, the planned tag (or N/A), highlights and migration notes. For a release, copy [the release notes template](docs/releases/TEMPLATE.md) to `docs/releases/<tag>.md`, replace its guidance with reviewed changes and migration steps, and include that file in the PR. Ordinary contribution PRs targeting `develop` can use N/A and need no version notes. Review relevant real Agent results for Skill behavior changes before merging; CI does not evaluate model output quality.
2. Merge the reviewed PR, then wait for **Skills CI on the resulting main commit**. A successful PR run or a run on `develop` is not sufficient.
3. In **Actions → Publish Skills → Run workflow**, select **main** and enter the full tag, for example `skills-v1.0.0`. The workflow must already exist on the default branch before this entry is available.
4. Leave **Only check release conditions** selected for a preflight that builds local artifacts but performs no GitHub release/tag writes. To actually publish, run it with that option unchecked. Review the complete Release body in the workflow summary before authorizing publication. Missing or empty committed notes stop both modes. A preflight does not reserve a version or approve a later run: publication repeats the checks against its own fixed commit.
5. Review the workflow summary and the resulting GitHub Release. Confirm its source SHA and release notes. The Release contains `skills-manifest.json` and one ZIP per Skill. Ordinary repository-based installation still works without downloading these assets. See the [artifact contract](docs/release-artifacts.md) for downstream consumption.

The workflow fixes the source to the dispatch commit and refuses to proceed if `main` has moved. It requires the latest `Skills CI` run for that SHA on `main` to succeed, including both **Lint and regressions** and **Browser smoke (no model)**; skipped jobs do not qualify. These are the release script's automated gates; normal PR review and branch-protection requirements still apply.

The tag must be unused and greater than existing stable Skills versions, including versions reserved by draft Releases. Publication creates the tag at the checked SHA and a draft Release named **VisActor Skills X.Y.Z**. After all ZIPs and the manifest are uploaded, their names, sizes, SHA-256 digests and uploaded state must match before the Release is published and marked as latest. An interrupted upload leaves a tag/draft for inspection, not a complete release for downstream synchronization. Both modes read `docs/releases/<tag>.md` from the exact source commit, ignoring local edits, and render the same body for identical inputs. The reviewed text is followed by the included Skills, source SHA and CI link; later releases also link the diff from the previous published stable Skills release. PR descriptions are not scraped and GitHub-generated notes do not replace migration instructions. See [release notes maintenance](docs/releases/README.md).

Publishing uses the workflow's built-in `GITHUB_TOKEN` with `contents: write` and `actions: read`; no personal token is needed. Release runs are serialized and never triggered by a push or merge. Repository rules can still deny tag/release creation; resolve the permission issue without bypassing protection.

If checks fail, fix the cause and start a new run once `main` CI passes. If GitHub returns an error or times out during publication, inspect the tag and Releases page before retrying: a write may have succeeded despite a lost response. Existing tags and Releases are never overwritten by this workflow. If a tag or draft exists, verify its SHA and rebuild from that exact commit in a fresh directory. Before completing the Release manually, verify every asset against the rebuilt manifest (including the manifest asset itself). Never publish a partial draft or delete/move a tag to make a retry pass. A missing server-reported asset digest stops publication; do not bypass the check.

CI and publication use `.github/scripts/package_skills.py`, which reads Git objects rather than working files. Both release modes retain local packages as a seven-day Actions artifact named `skills-release-preview`; this is diagnostic output, not a formal release.

Local verification does not publish:

```bash
uv run --locked ruff check .github/scripts tests/test_release.py tests/test_release_packages.py
uv run --locked pytest tests/test_release.py tests/test_release_packages.py -q
uv run --locked python .github/scripts/package_skills.py --commit HEAD --tag skills-v1.0.0 --output .cache/release-preview
```

Use a new output directory for each build. The local command treats the tag as manifest metadata and never creates a Git tag.

## Before committing

Enable repository hooks:

```bash
git config core.hooksPath .githooks
```

Hooks check staged whitespace, run Ruff for Python/tooling changes and require a Conventional Commit subject. Python checks require `uv` on PATH. Run relevant tests before committing; hooks do not run model tasks or the complete test suite.

Explain the task or defect, the behavior changed and why the selected checks protect it. Include commands, case ids and review outcomes; for agent runs, include the host/model and Skill revision. Report failures and skipped checks. Add cases for distinct behaviors, not just to increase the count. Keep credentials, private data and raw execution evidence out of commits.
