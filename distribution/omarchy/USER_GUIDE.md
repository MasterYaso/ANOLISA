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

## First launch

Click **ANOLISA** in the bar, then **开始设置**. The wizard uses Omarchy's default terminal. You can skip either step independently. **稍后** saves your choice and lets you return through **设置**.

1. **cosh**. Enter `1`, read the instructions, then press Enter to open cosh. Use `/auth` to configure your model service, `/status` to inspect it, and `exit` to return to the wizard. Press Enter at the first prompt to skip.
2. **Qoder**. Enter `1` to continue or press Enter to skip. The wizard selects a verified Qoder CLI 1.1.84 and offers to install the pinned version if missing. **在 Qoder CLI 中配置** opens Qoder for browser or PAT authentication. **直接输入 Qoder PAT** uses hidden input in the wizard. **稍后设置** defers configuration, available later under **设置 → 设置 Qoder**. Upgrades retain the existing mode and credentials.
3. **Optional connection check**. The wizard can open a terminal session. After an actual answer, return to the wizard to record the result and time manually.

## Questions and tasks

Open the working terminal from the panel. **Enter `/agent` on its own and press Enter**, then type a question at `◆` and press Enter to send it. Try “Explain what pwd does without executing a command.” Esc returns to the normal prompt. Enter `exit` to close cosh.

Open Qoder from the panel and test it in a disposable project. Ask it to read a text file with Bash and write `RESULT.md`. Inspect the file and component records. If the safety service is unavailable, the enhanced entry stops and points to diagnostics.

Open **插件说明** in the panel footer to view common commands and component roles.

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
