# Changelog

## [Unreleased]

- Detect upload failures caused by the workspace not being on a paid
  plan (or a trial of one) more reliably, including failures reported
  through the API's error body or during URL-based layer imports, and
  show a clearer message explaining how to start a trial or upgrade
- Show the error detail returned by the Felt API when an upload fails,
  instead of only Qt's generic network error string

## [3.2.1] - 2026-06-17

- Fix QGIS plugin repository security scan issues blocking release:
  add an explicit timeout to the OAuth callback unblock request, and
  replace the high-entropy multipart form boundary with a readable
  constant

## [3.2.0] - 2026-06-17

- Add support for QGIS 4.x (Qt6-based) releases, while remaining
  compatible with QGIS 3.22 and later

## [1.0.0] - 2023-06-21

- Initial release

