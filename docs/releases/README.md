# Release notes

For each planned Skills release, copy [TEMPLATE.md](TEMPLATE.md) to
`docs/releases/skills-vMAJOR.MINOR.PATCH.md`. Replace the guidance with actual
changes, migration steps and known limitations. Write “None” where a section
does not apply. Review and commit the file in the `develop` → `main` release PR.
Tooling-only PRs need no version record; the template is not a release.

Both preflight and publication read the version file from the exact source
commit. Untracked files, local edits and notes for a different version cannot
satisfy this requirement. Missing, empty or non-regular files stop the run.
Content quality and completeness remain part of human PR review.

The workflow summary shows the full Release body before publication: reviewed
notes, included Skills, source commit, CI link and (after the first release) a
diff link from the previous published stable Skills release. The target tag in
that diff link becomes available when the release creates it. For the same
commit, version and previous release, preflight and publication use identical
body generation. A new main commit requires a fresh preflight and review.

Do not add a duplicate CHANGELOG.md or rely on GitHub-generated PR lists for
migration guidance. Published versions and their notes are immutable; document
corrections in a new version. The script cannot enforce that reviewers approved
the prose; follow the repository's PR review process.
