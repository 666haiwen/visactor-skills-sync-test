# Isolated sync test 1.0.1

## New capabilities

None. This is a synchronization test release, not a VisActor production release.

## Fixes

Add a test-only resource to person-poster to change its content fingerprint.
The other three Skill packages retain the same content fingerprints. The
expected downstream result is one update and three skips, then four skips on
a repeated run.

## Breaking changes and migration

None. Do not use these test packages to replace production installations.

## Known limitations

This test verifies publication and incremental synchronization, not generated
poster quality. No scheduled publishing is enabled.
