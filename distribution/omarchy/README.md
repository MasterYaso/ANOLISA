# ANOLISA - AI Assistant (Omarchy experimental integration)

[简体中文](README_zh.md)

A native Omarchy bar dropdown that opens cosh and an AW-managed Qoder session.
Security and Tokenless details come from the components' public CLI interfaces.
This integration does not replace Omarchy's desktop or terminal emulator.

## Install 0.1.1

Open a terminal as the logged-in desktop user on Omarchy x86_64. From the clone:

```bash
cd distribution/omarchy
bash ./install
```

The script downloads the `omarchy-v0.1.1` GitHub Release asset, checks it against
`SHA256SUMS` from this directory and runs the installer. If you already have the
archive, pass `--archive /path/to/anolisa-omarchy-0.1.1.tar.gz` to the same script.

As the logged-in Omarchy desktop user, extract the candidate and run `./install`.
It installs the bundled programs into a private user prefix, enables the native
bar plugin and uses sudo once to deploy the root-required code-safety service.
The safety daemon runs from a root-owned directory. The candidate contains the
compiled programs. Open the bar widget after installation to configure cosh and
Qoder independently, or defer setup. The wizard opens a compatible Qoder CLI
1.1.84, or offers to install it if missing. Sign in within Qoder or provide a
PAT through the ANOLISA wizard. The **插件说明** entry shows the common commands.

The payload includes cosh, AW, two AW Providers, the sec-core code-scanning
runtime, Tokenless and a pinned Qoder CLI. Qoder is third-party software subject
to its own terms. A saved PAT indicates local configuration, not a successful
model request. cosh has separate model authentication through `/auth`.

`anolisa-omarchy setup` opens the setup wizard. Use `--component cosh` or
`--component qoder` to configure one component. Use `help` for component roles,
`status` for current state, and `doctor` for actionable diagnostics. `status --json`
and `doctor --json` retain machine-readable reports.

- [User guide and acceptance](USER_GUIDE.md)
- [Source build and packaging](BUILDING.md)

## Remove the bar widget

```bash
omarchy plugin remove community.anolisa
```

To stop the service and disable startup, run
`sudo systemctl disable --now anolisa-omarchy-security.service`. These commands
preserve the installed programs, credentials and statistics for later reuse.

## Development

Keep changes in this distribution directory. Reuse `src/cosh-ng`, `src/aw`,
`src/agent-sec-core`, `src/tokenless` and `providers/`; do not fork their logic.
Run `python -m pytest distribution/omarchy/tests` on Linux with Python 3.11.6.
Follow the repository contribution and documentation standards before a PR.

For local visual checks, use a development environment with
`PySide6-Essentials==6.10.1` and run
`python distribution/omarchy/tests/check_panel.py --output /tmp/anolisa-panel-check`.
It renders the real QML panel, exercises its mouse actions, checks missing
metrics and exports PNGs. It does not connect to a VM or verify Quickshell's
native popup host. PySide6 is a development dependency, not a laptop dependency.

The dropdown is a launcher and local view, not an Agent. The Qoder action invokes
`aw run` with an owned configuration. Hook coverage applies to the configured
native Qoder tools; it is not an OS sandbox. cosh does not automatically route
natural-language requests into this Qoder process. Closing a terminal ends that
foreground session; this version does not advertise background task recovery.

The panel uses a fixed charcoal and mint palette to preserve action hierarchy
across desktop themes. `AssistantPanel.qml` is the actual independently
renderable view; `Widget.qml` connects it to the native bar and runtime.
`AssistantPopup.qml` adapts Omarchy's `shell/Ui/PopupCard.qml` to retain native
anchoring, focus and outside-click dismissal. Its MIT notice is included in
`plugin/OMARCHY-LICENSE`.

License: [Apache-2.0](../../LICENSE), with MIT for the adapted Omarchy code.
Bundled components retain their licenses.
