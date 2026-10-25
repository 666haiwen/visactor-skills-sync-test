# Isolated sync test 1.1.0

## New capabilities

Add sync-verification, a test-only installation probe, to verify automatic
discovery and creation of a newly added Skill after the initial sync baseline.
This is not a VisActor production release.

## Fixes

Add a test-only resource to person-poster to change its content fingerprint.
The other three Skill packages retain the same content fingerprints. Expected
downstream result: one creation, one update and three skips, then five skips
on a repeated run.

## Breaking changes and migration

None. Do not use these test packages to replace production installations.

## Known limitations

This test verifies publication and incremental synchronization, not generated
output quality. No scheduled publishing is enabled.
