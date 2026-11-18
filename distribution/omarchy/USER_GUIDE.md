# ANOLISA - AI Assistant

[中文版](USER_GUIDE_zh.md)

Open cosh and Qoder from the Omarchy bar and work in their terminals. Use the panel to review Qoder Bash safety checks and Tokenless records.

## Install

Use an Omarchy desktop on Linux x86_64 with Python 3.11 or later. Extract the candidate and run these commands as the desktop user in a graphical session:

```bash
./install
~/.local/bin/anolisa-omarchy status
```

The installer verifies the candidate, checks dynamic libraries, and uses sudo to install missing dependencies when the local pacman file index identifies a unique package. It uses sudo for the system safety service, then enables the bar widget. If the index cannot identify a package, the terminal names the missing library so you can verify the target repositories before retrying.

`./install --non-interactive` exits when sudo needs interaction. `./install --no-enable` deploys user files and skips system dependency installation, service setup, and desktop activation. Configure model access after installation.

## Interface language

The 0.1.2 candidate defaults to English. In the dropdown, open **Settings →
Language / 语言** and select **English** or **简体中文**. The view updates after
the selection is saved, and the choice survives closing the panel and rebooting.

```bash
anolisa-omarchy language
anolisa-omarchy language zh-CN
anolisa-omarchy language en-US
```

The preference lives in `$XDG_CONFIG_HOME/anolisa-omarchy/ui.json`, or
`~/.config/anolisa-omarchy/ui.json` when XDG_CONFIG_HOME is unset. It has mode 0600.
New plugin commands and setup terminals use the saved language. New cosh sessions
receive `COSH_SHELL_LANG`; existing terminal sessions are not restarted. This does
not change system LANG, shell startup files, model credentials or Qoder's own UI.
Interface language does not restrict the language of your questions.

## First launch

Click **ANOLISA** in the bar, then **Start setup**. The wizard uses Omarchy's default terminal. You can skip either step independently. **Later** saves your choice and lets you return through **Settings**.

1. **cosh**. Enter `1`, read the instructions, then press Enter to open cosh. Use `/auth` to configure your model service, `/status` to inspect it, and `exit` to return to the wizard. Press Enter at the first prompt to skip.
2. **Qoder**. Enter `1` to continue or press Enter to skip. If Qoder is missing, choose recommended version 1.1.84 (default), the latest official version, or setup later. The archive contains no Qoder executable. **Configure in Qoder CLI** opens Qoder for browser or PAT authentication. **Enter your Qoder PAT here** uses hidden input in the wizard. **Set up later** defers configuration, available later under **Settings → Set up Qoder**. Upgrades retain the existing mode and credentials.
3. **Optional connection check**. The wizard can open a terminal session. After an actual answer, return to the wizard to record the result and time manually.

## Questions and tasks

Open the working terminal from the panel. **Enter `/agent` on its own and press Enter**, then type a question at `◆` and press Enter to send it. Try “Explain what pwd does without executing a command.” Esc returns to the normal prompt. Enter `exit` to close cosh.

Open Qoder from the panel and test it in a disposable project. Ask it to read a text file with Bash and write `RESULT.md`. Inspect the file and component records. If the safety service is unavailable, the enhanced entry stops and points to diagnostics.

Open **Help** in the panel footer to view common commands and component roles.

```bash
~/.local/bin/anolisa-omarchy setup
~/.local/bin/anolisa-omarchy setup --component cosh
~/.local/bin/anolisa-omarchy setup --component qoder
~/.local/bin/anolisa-omarchy auth
~/.local/bin/anolisa-omarchy help
~/.local/bin/anolisa-omarchy status
~/.local/bin/anolisa-omarchy doctor
```

When starting the same enhanced entry from a terminal, separate Qoder arguments with `--`. Use `--native-settings` to merge a native settings file.

```bash
~/.local/bin/anolisa-omarchy qoder
~/.local/bin/anolisa-omarchy qoder --native-settings ./qoder.settings.json -- --version
```

## Dashboards

- **sec-core** shows up to 200 recent service scan records and risk findings. Execution blocks require independent evidence and display `—` when that evidence is absent.
- **Tokenless** shows before and after sizes and estimated reductions for up to 200 recent records in the managed store of the current user. The scope is tool content. A valid zero appears as `0`; missing data appears as `—`.

## Upgrade and troubleshoot

Run `./install` from the new archive to upgrade demo.2. The installer recognizes the old managed configuration, saves it as `aw.demo2.json`, and preserves credential files and component records. An edited `aw.json` stops activation and the installer prints the location of a proposed file for comparison.

An ordinary installation failure attempts to restore the previous widget, application references, managed configuration, and system service. Consult the terminal and `anolisa-omarchy/installation.json` under the user state directory for the failed phase and rollback results. Pacman records system dependencies separately. After a power loss or forced termination, inspect the receipt and any pending service recovery record before retrying.
Use `help` for component roles and entry points, `status` for installation and current state, and `doctor` for troubleshooting. Plugins and automation can use `status --json` or `doctor --json`. An actual answer verifies the model connection.

## Optional Qoder installation

Open **Settings → Qoder version** to install or switch versions. The default is
the fixed, tested 1.1.84 build. **Latest** resolves the official release manifest
at installation time and verifies its SHA-256. A future untested build is labelled
as unverified. Managed installations do not update silently; use the same entry
again to update or return to the recommended version.

```bash
anolisa-omarchy qoder-install --channel recommended
anolisa-omarchy qoder-install --channel latest
```

Programs live under `$XDG_DATA_HOME/anolisa-omarchy/qoder`, or
`~/.local/share/anolisa-omarchy/qoder`. Account files stay in the existing private
configuration directory. Changing versions and upgrading the plugin preserve them.
Downloads require access to Qoder's official HTTPS service and show progress.
The plugin checks both the archive checksum and the executable's reported version.

For the native Arch package candidate:

```bash
sudo pacman -U ./anolisa-omarchy-0.1.2-1-x86_64.pkg.tar.zst
anolisa-omarchy enable
```

Before removing that package, run `anolisa-omarchy disable`, then
`sudo pacman -R anolisa-omarchy`. This preserves separately downloaded Qoder,
account configuration and statistics. The archive installer and native package
are separate installation modes; remove the old mode before switching.
