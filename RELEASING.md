# Releasing

This document describes how a new version of the **Add to Felt** plugin is
released.

## Versioning

The **git tag is the source of truth for the version.** When a release is
published, the [`release.yml`](.github/workflows/release.yml) workflow runs
`qgis-plugin-ci release <tag>`, which stamps the tag name into the packaged
`felt/metadata.txt` `version=` field — overriding whatever value is committed
there.

- Tags use **no `v` prefix** (e.g. `3.2.1`, not `v3.2.1`). The tag name becomes
  the version string verbatim, so a `v` prefix would ship a version literally
  named `v3.2.1`.
- The `version=` field in `felt/metadata.txt` is **cosmetic** — `qgis-plugin-ci`
  overrides it with the tag name at release time. Keep it consistent with the
  tag for hygiene, but the tag is what determines the shipped version.
- `CHANGELOG.md` is **not** cosmetic. At release time `qgis-plugin-ci` reads it
  and injects the matching version's notes into the packaged `metadata.txt`
  `changelog=` field, which QGIS surfaces to users in the Plugin Manager. So the
  `changelog=` field in `metadata.txt` is intentionally left empty and must not
  be hand-edited — maintain release notes in `CHANGELOG.md` only.

## Steps

1. **Update the changelog and metadata on a branch.** Move items out of
   `[Unreleased]` in `CHANGELOG.md` into a new `## [<version>] - <date>` section,
   and bump `version=` in `felt/metadata.txt` to match. Open a PR and merge to
   `main`. The release will still build without this, but the `CHANGELOG.md`
   entry is what populates the user-visible changelog in the published package
   (see Versioning above), so do it before tagging. The `version=` bump itself is
   cosmetic hygiene since the tag overrides it.

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
- **If plugins.qgis.org rejects the upload** (e.g. its automated security scan
  blocks the package), do **not** reuse the same version number to resubmit.
  The GitHub tag/release for that version is already cut against the old code
  and should be treated as immutable. Fix the issues on a branch, bump to a new
  patch version (e.g. `3.2.0` → `3.2.1`) with a matching `CHANGELOG.md` entry,
  cut a new tag/release, and upload that. Leave the blocked release in place as
  a record of the attempt.
