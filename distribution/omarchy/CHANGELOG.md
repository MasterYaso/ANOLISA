# Changelog

[Simplified Chinese](CHANGELOG_zh.md)

This file records user-visible changes to the Omarchy distribution integration.
The version below is prepared for review; it has not been published.

## [0.1.3] - 2026-11-20

### Added

- Add an Omarchy top-bar dropdown for cosh, AW-managed Qoder sessions, security
  scan details and Tokenless processing records.
- Provide English by default with a Chinese option, account and model setup,
  component help, status and diagnostics.
- Provide a prebuilt Linux x86_64 installer and verified offline installation.
  Qoder is optional and downloaded separately from its official source.

### Fixed

- Keep Help visible when opened directly from Home.
- Prevent mise's missing-command handler from replacing cosh's natural-language
  handling in the launched child process.

### Compatibility

- Only Omarchy Linux x86_64 is supported. Account configuration and statistics
  are per-user; the code-safety service uses root-owned installed files.
- The dropdown does not retain closed terminal sessions. Scan counts are not
  execution-block counts; Tokenless estimates do not represent billing savings.
