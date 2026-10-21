# VisActor Skills maintenance

- Use `main` as the default, user-facing stable branch and `develop` for day-to-day maintenance. Publish reviewed updates through a `develop` → `main` pull request. Start new contribution branches from the latest `origin/develop` and target PRs to `develop`.
- Runtime Skills live in `skills/<skill-name>/`, with a lowercase hyphenated directory matching the `SKILL.md` frontmatter name. Each Skill must work when copied independently without sibling Skill or maintenance-directory imports.
- Keep tests, fixed Agent tasks and generated reports outside Skill directories. Put Skill-specific Python regressions under `tests/<skill_name>/` (hyphens become underscores); shared tooling/packaging checks and current Node.js integrations live at the test root.
- Keep both root READMEs aligned with the maintained Skills, install commands and runtime requirements. Document externally maintained Skills as upstream links rather than copying them here.
- Document actual fixed-task and browser-smoke coverage; installing a Skill does not imply it has either. Use mature agents for task execution; do not add a model API harness or host-specific batch runners.
- Maintain fixed browser smoke cases under `tests/browser/cases/<skill>/<case>/`, with configuration, inputs and expectations together. Browser scripts and dependencies live under `tests/browser/`; do not embed case-specific inputs in the runner.
- Keep fixed Agent tasks under `cases/<skill-name>/<case-name>/`, with `prompt.md`, `inputs/`, input hashes in `fixtures.json` and a README containing acceptance points. Follow [the case guide](cases/README.md); allow multiple correct outputs instead of requiring page or pixel equality.
- Preserve user changes. Do not commit or publish unless requested.
- Use `uv run pytest` for Python tests and `uv run ruff check` for maintained Python tooling.
- Test stable behavior; do not snapshot large instruction documents. Generalize Skill fixes from observed failures; do not add runtime rules keyed to a case id, exact fixture, prompt string or evaluation path.
- For evaluation, expose only the selected skill and task inputs to the agent, never expected answers.
- Keep observable execution evidence locally, redact credentials and distinguish automated checks from human visual review.
- Do not restore the historical VMind SDK or depend on leftover local packages. Earlier versions remain in Git history and releases.

## Local development workspaces

- Use one ignored `.cache/skill-dev/<skill-name>/<run-name>/` directory per experiment. Follow [local debugging](docs/debugging.md); `.cache/` is already ignored.
- Keep copied inputs in `inputs/`, generated files in `outputs/`, screenshots in `screenshots/` and available session/tool logs in `logs/`. Record the Skill revision or local diff, host/model, checks and outcome in `notes.md`; note logs the host cannot export. Never put credentials in shared evidence.
- Edit source Skills under `skills/`, then refresh the installed copy before retesting. Copy fixed inputs into the run workspace; do not modify originals during a run. Keep acceptance guidance outside the generation workspace.
- Promote stable tasks to `cases/`, deterministic regressions to `tests/`, and reviewed showcase results to `examples/`. Keep drafts, raw logs and caches local.
- Clean only directories owned by the current task. Do not delete another session's files or historical evidence automatically.

## Showcase examples

- Keep curated examples under `examples/<skill-name>/<case-name>/`, outside runtime Skills and test tooling. Follow the [example guide](examples/README.md). Keep one README per example, written in the case's language; do not require separate translated copies.
- Keep example READMEs focused on the task, prompt, inputs, result, preview and usage requirements. Keep migration history, resource-adaptation details and internal verification records outside the public case descriptions; retain only data limitations that affect usage.
- Review the actual output before presenting it as a showcase. Keep raw session logs and caches local. Examples are not automatically regenerated or treated as CI snapshots.

## Versioning

- Version the Skills maintained here together at repository level. External Skills use their owning repositories' versions. Do not maintain separate version numbers for individual Skills.
- Ordinary Skill edits are identified by commits; a new release tag is not required for each edit.
- Mark each formal Skills release with a Git tag that identifies the complete repository snapshot, including Skill instructions, references, templates and scripts. Preserve published tags and historical VMind SDK tags; do not move or reuse them.
- Use a release tag or commit SHA to identify the Skill version when reporting or reproducing results. A branch name alone can change over time.
- Keep Skill release versions distinct from dependency versions such as VChart and VTable. Updating a library does not assign its version number to the Skill.
