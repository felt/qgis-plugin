# Releasing

This document describes how a new version of the **Add to Felt** plugin is
released.

## Versioning

The **git tag is the source of truth for the version.** When a release is
published, the [`release.yml`](.github/workflows/release.yml) workflow runs
`qgis-plugin-ci release <tag>`, which stamps the tag name into the packaged
`felt/metadata.txt` `version=` field — overriding whatever value is committed
there.

- Tags use **no `v` prefix** (e.g. `3.2.0`, not `v3.2.0`). The tag name becomes
  the version string verbatim, so a `v` prefix would ship a version literally
  named `v3.2.0`.
- The `version=` field in `felt/metadata.txt` and the entries in
  `CHANGELOG.md` are cosmetic — they do not drive the release and are not
  prominently surfaced to users. Keep them consistent for hygiene, but the tag
  is what matters.

## Steps

1. **(Optional) Update the changelog and metadata on a branch.** Move items out
   of `[Unreleased]` in `CHANGELOG.md` into a new `## [<version>] - <date>`
   section, and bump `version=` in `felt/metadata.txt` to match. Open a PR and
   merge to `main`. This is cosmetic hygiene, not required for the release to
   succeed.

2. **Create a GitHub Release** with a new tag (e.g. `3.2.0`), targeting `main`.
   Publishing the release triggers [`release.yml`](.github/workflows/release.yml),
   which builds `felt.<version>.zip`, stamps `version=<tag>` into its
   `metadata.txt`, and attaches the zip to the GitHub release.

3. **Manually upload the zip to plugins.qgis.org.** Nothing in this repo
   publishes to the QGIS plugin repository — the workflow only attaches the zip
   to the GitHub release. Download `felt.<version>.zip` from the release and
   upload it at <https://plugins.qgis.org/plugins/felt/> (logged in with an
   account that has rights on the plugin). This is what makes the new version
   available to users in QGIS' Plugin Manager.

## Notes

- `release.yml` passes only `--github-token`, so it does **not** publish to
  plugins.qgis.org; that step is manual (see step 3).
- On every push and pull request, [`build.yml`](.github/workflows/build.yml)
  builds an `-alpha` package via `qgis-plugin-ci package` and uploads it as a CI
  artifact (with a download link posted on the PR). This is for testing
  pre-release builds and is not part of the release path.
