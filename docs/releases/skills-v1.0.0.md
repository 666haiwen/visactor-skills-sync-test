# VisActor Skills 1.0.0

This is the first repository-level Skills release, separate from the historical
VMind SDK versions. It establishes a fixed snapshot of the three Skills already
available on `main`; this release does not change their runtime instructions,
templates or scripts relative to the preceding `main` snapshot.

## Capabilities

- **chart-storytelling**: HTML data stories and Web-PPT presentations, including
  chart-based scrollytelling and annotations.
- **editorial-magazine**: editable magazine-style HTML and PNG sequences for
  news, biographies, travel, outfits and other editorial stories.
- **life-chronicle**: biography posters with photo-wall, center-grid and
  photo-ring layouts, plus editable timelines.
- Curated examples now include six magazine cases and four biography cases,
  alongside the existing CO2 story and Las Vegas Web-PPT examples.
- Each Release supplies `skills-manifest.json` and one self-contained ZIP per
  Skill. Per-Skill content fingerprints allow distributors to identify changes
  independently of the repository version.

## Release workflow fixes

- Publication requires successful CI for the exact `main` commit and an unused
  Skills version. Explicit tag creation prevents silently reusing a tag created
  concurrently by another publisher.
- Preflight displays the full reviewed release notes. Packages are uploaded to
  a draft and verified before the Release becomes available to consumers.

## Migration

There are no additional Skill renames, removals or runtime changes relative to
the preceding `main` snapshot. Users moving from older repository snapshots
should account for these earlier changes:

- If `data-storytelling` is installed, remove that installed copy through your
  Skill manager, install `chart-storytelling`, and update prompts or local
  configuration that refer to the former name.
- VChart and VTable Skills are maintained in `VisActor/VChart` and
  `VisActor/VTable`. Replace old copies from this repository with the upstream
  `vchart-development-assistant` and `vtable-development-assistant` Skills;
  they are not included in this release's packages.
- This release is not a VMind SDK upgrade. Existing SDK users should continue
  using their historical SDK release; the Skills repository does not provide
  an SDK compatibility layer.

For installation commands and runtime dependencies, see the
[README at this version](https://github.com/VisActor/skills/blob/skills-v1.0.0/README.md).
Keep the complete Skill directory, including its references, templates and
scripts, when installing from a ZIP. Record the tag or commit when reproducing
results; default branch installations can receive subsequent changes.

## Known limitations

- Skills require a capable host Agent and its model/tool access. This repository
  does not supply a hosted Agent service or a model API harness.
- Browser previews, external libraries/fonts, image retrieval and image
  generation depend on the requirements of the selected Skill and host.
  Web-PPT is a browser presentation, not a `.pptx` export.
- CI checks deterministic regressions and chart-storytelling browser smoke; it
  does not evaluate model-generated output quality. Editorial-magazine and
  life-chronicle have script regressions but no fixed browser smoke coverage.
- Release artifacts define the distribution interface. Automatic publication
  to third-party Skill platforms is not part of this release.
