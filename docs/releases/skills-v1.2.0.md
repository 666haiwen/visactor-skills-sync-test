# Isolated synchronization test 1.2.0

## New capabilities

Add sync-mapping-probe to test automatic discovery and creation from a formal
release manifest. This is a disposable personal fork, not a VisActor release.

## Fixes

Change only the person-poster test marker to verify a service account can update
an adopted, user-owned package after receiving package-maintainer rights.
Unchanged Skills should keep their fingerprints and market versions.

## Breaking changes and migration

None. Do not copy these test-only packages or markers upstream.

## Known limitations

This validates publication, mapping and content integrity, not generated output
quality. Scheduled publication remains disabled.
