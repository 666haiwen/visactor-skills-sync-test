# VisActor Skills maintenance

- Keep `develop` as the default and primary maintenance branch. Start new contribution branches from the latest `origin/develop` and target PRs to `develop`.
- Runtime Skills live in `skills/<skill-name>/`, with a lowercase hyphenated directory matching the `SKILL.md` frontmatter name. Each Skill must work when copied independently without sibling Skill or maintenance-directory imports.
- Keep tests, fixed evaluation tasks and generated reports outside Skill directories. Put Skill-specific Python regressions under `tests/<skill_name>/` (hyphens become underscores); shared tooling/packaging checks and current Node.js integrations live at the test root.
- Keep both root READMEs aligned with the maintained Skills, install commands and runtime requirements. Document externally maintained Skills as upstream links rather than copying them here.
- Runtime Skill discovery does not imply model-case, browser-smoke or API script support. Document coverage accurately and verify new adapters before claiming support.
- Maintain fixed browser smoke cases under `evals/smoke/<skill>/<case>/`, with configuration, inputs and expectations together. Keep model tasks under `evals/cases/`; do not embed case-specific data or configuration in the smoke runner.
- Preserve user changes. Do not commit or publish unless requested.
- Use `uv run pytest` for Python tests and `uv run ruff check` for maintained Python tooling.
- Test stable behavior; do not snapshot large instruction documents. Generalize Skill fixes from observed failures; do not add runtime rules keyed to a case id, exact fixture, prompt string or evaluation path.
- For evaluation, expose only the selected skill and task inputs to the agent, never expected answers.
- Keep observable execution evidence locally, redact credentials and distinguish automated checks from human visual review.
- Do not restore the historical VMind SDK or depend on leftover local packages. Earlier versions remain in Git history and releases.

## Showcase examples

- Keep curated examples under `examples/<skill-name>/<case-name>/`, outside runtime Skills and eval tooling. Follow the [example guide](examples/README.md). Keep one README per example, written in the case's language; do not require separate translated copies.
- Keep example READMEs focused on the task, prompt, inputs, result, preview and usage requirements. Keep migration history, resource-adaptation details and internal verification records outside the public case descriptions; retain only data limitations that affect usage.
- Review the actual output before presenting it as a showcase. Keep raw session logs and caches local. Examples are not automatically regenerated or treated as CI snapshots.

## Versioning

- Version the Skills maintained here together at repository level. External Skills use their owning repositories' versions. Do not maintain separate version numbers for individual Skills.
- Ordinary Skill edits are identified by commits; a new release tag is not required for each edit.
- Mark each formal Skills release with a Git tag that identifies the complete repository snapshot, including Skill instructions, references, templates and scripts. Preserve published tags and historical VMind SDK tags; do not move or reuse them.
- Use a release tag or commit SHA to identify the Skill version when reporting or reproducing results. A branch name alone can change over time.
- Keep Skill release versions distinct from dependency versions such as VChart and VTable. Updating a library does not assign its version number to the Skill.
