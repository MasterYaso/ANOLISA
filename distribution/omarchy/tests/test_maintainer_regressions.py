"""Exercise cache failures and interrupted upgrades through the packaged installer."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from test_demo3 import program
from test_integration import load
from test_integration import paths as paths
from test_release import candidate as candidate


@pytest.mark.parametrize("fault", ["json", "write", "linked", "permissions"])
def test_display_cache_failure_does_not_hide_qoder(
    paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    runtime = load("runtime")
    binary = program(runtime.agents, paths["prefix"], monkeypatch)
    monkeypatch.setattr(runtime, "healthy", lambda *_: True)
    monkeypatch.setattr(
        runtime,
        "dashboards",
        lambda *_: ({"available": True}, {"available": True, "state": "empty"}),
    )
    monkeypatch.setattr(runtime, "check_managed_config", lambda *_: {})
    assert runtime.status(paths)["qoder"]["installation"] == "compatible"
    cache = runtime.agents.data_directory() / "display-inspection.json"
    if fault == "json":
        cache.write_text("{")
    elif fault == "write":
        cache.unlink()

        def unavailable(*_args: object, **_kwargs: object) -> None:
            raise PermissionError("Cache is read-only")

        monkeypatch.setattr(runtime.agents, "atomic_write", unavailable)
    elif fault == "linked":
        cache.unlink()
        other = tmp_path / "other.json"
        other.write_text("must not read or change")
        cache.symlink_to(other)
    else:
        cache.chmod(0o644)
    assert runtime.status(paths)["qoder"]["installation"] == "compatible"
    assert runtime.agents.inspect(binary, "existing")["installation"] == "compatible"
    if fault == "linked":
        assert other.read_text() == "must not read or change"
    # Display-only recovery must not weaken the full check before execution.
    binary.write_text("changed executable")
    assert runtime.agents.inspect(binary, "existing")["installation"] == "incompatible"


@pytest.fixture
def interrupted_upgrade(candidate: Path, tmp_path: Path) -> dict:
    """Install A, then kill B immediately after switching the managed release link.

    Only external desktop/root programs are replaced. Both installers load their
    actual pinned Python modules; the crash is injected in a separate process.
    """
    original = candidate.parent.parent / "anolisa-omarchy-0.1.3"
    bundles = []
    for name, version in (("a", "0.1.2"), ("b", "0.1.3")):
        bundle = tmp_path / name
        shutil.copytree(original, bundle)
        manifest = bundle / "payload/plugin/manifest.json"
        widget = json.loads(manifest.read_text())
        widget["version"] = version
        manifest.write_text(json.dumps(widget))
        health = bundle / "payload/bin/agent-sec-daemon-health"
        health.write_text("#!/bin/sh\nexit 0\n")
        for executable in ("aw", "cosh", "tokenless", "agent-sec-cli"):
            (bundle / "payload/bin" / executable).write_text("#!/bin/sh\nexit 0\n")
        metadata = json.loads((bundle / "bundle.json").read_text())
        metadata["version"] = version
        metadata["files"] = {
            p.relative_to(bundle / "payload").as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (bundle / "payload").rglob("*")
            if p.is_file()
        }
        (bundle / "bundle.json").write_text(json.dumps(metadata))
        bundles.append(bundle)
    home, tools = tmp_path / "home", tmp_path / "tools"
    home.mkdir()
    tools.mkdir()
    # Fake OS programs make this test safe on CI without sudo or a desktop.
    tool = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
if name == 'sudo':
    sys.stdin.buffer.read()
    action = sys.argv[sys.argv.index('-c') + 3]
    with open(os.environ['TEST_ACTIONS'], 'a') as log:
        log.write(action + '\\n')
    journal = Path(os.environ['TEST_JOURNAL'])
    if action == 'prepare':
        journal.write_text('pending')
    elif action in ('recover', 'commit', 'rollback'):
        journal.unlink(missing_ok=True)
elif name == 'omarchy-shell' and sys.argv[-1] == 'listPlugins':
    print(json.dumps([{{'id': 'community.anolisa'}}]))
elif name == 'ldd':
    print('statically linked')
"""
    for name in ("sudo", "omarchy", "omarchy-shell", "omarchy-launch-terminal", "ldd", "systemctl"):
        target = tools / name
        target.write_text(tool)
        target.chmod(0o755)
    env = dict(
        os.environ,
        HOME=str(home),
        PATH=f"{tools}:/usr/bin:/bin",
        TEST_ACTIONS=str(tmp_path / "actions"),
        TEST_JOURNAL=str(tmp_path / "journal"),
    )
    for key in ("DATA", "CONFIG", "STATE", "RUNTIME"):
        env[f"XDG_{key}_" + ("DIR" if key == "RUNTIME" else "HOME")] = str(tmp_path / key.lower())

    def run(bundle: Path, *arguments: str, crash: bool = False) -> subprocess.CompletedProcess:
        if crash:
            script = """
import os, runpy, sys
ns = runpy.run_path(sys.argv[1])
original = ns['replace_link']
def switch(*args):
    original(*args)
    os._exit(77)
ns['main'].__globals__['replace_link'] = switch
sys.argv = [sys.argv[1], '--non-interactive']
ns['main']()
"""
            command = [sys.executable, "-I", "-B", "-c", script, str(bundle / "install.py")]
        else:
            command = ["bash", str(bundle / "install"), "--non-interactive", *arguments]
        return subprocess.run(command, env=env, text=True, capture_output=True, timeout=30)

    a, b = bundles
    first = run(a)
    assert first.returncode == 0, first.stdout + first.stderr
    current = tmp_path / "data/anolisa-omarchy/current"
    previous = current.resolve()
    # Account data is outside release deployment and must survive recovery.
    account = home / ".qoder/account-fixture"
    account.parent.mkdir()
    account.write_text("existing account")
    killed = run(b, crash=True)
    assert killed.returncode == 77, killed.stdout + killed.stderr
    plugin = home / ".config/omarchy/plugins/community.anolisa"
    assert current.resolve() != previous
    assert (plugin / "manifest.json").read_bytes() == (
        previous / "plugin/manifest.json"
    ).read_bytes()
    assert Path(env["TEST_JOURNAL"]).exists()
    return dict(
        run=run,
        b=b,
        plugin=plugin,
        previous=previous,
        current=current,
        account=account,
        actions=Path(env["TEST_ACTIONS"]),
        journal=Path(env["TEST_JOURNAL"]),
    )


@pytest.mark.parametrize("widget_state", ["previous", "current", "missing"])
def test_packaged_recovery_accepts_unchanged_previous_widget(
    interrupted_upgrade: dict, widget_state: str
) -> None:
    case = interrupted_upgrade
    target = case["current"].resolve()
    retry = case["run"](case["b"])
    assert retry.returncode != 0 and "Existing plugin differs" in retry.stderr
    if widget_state != "previous":
        shutil.rmtree(case["plugin"])
        if widget_state == "current":
            shutil.copytree(case["current"] / "plugin", case["plugin"])
            (case["plugin"] / ".anolisa-omarchy-owned").write_text(
                case["current"].resolve().name + "\n"
            )
    result = case["run"](case["b"], "--recover")
    assert result.returncode == 0, result.stdout + result.stderr
    assert case["current"].resolve() == target
    assert json.loads((case["plugin"] / "manifest.json").read_text())["version"] == "0.1.3"
    assert case["actions"].read_text().splitlines()[-3:] == ["recover", "prepare", "commit"]
    assert not case["journal"].exists()
    assert case["account"].read_text() == "existing account"


@pytest.mark.parametrize(
    "change", ["widget", "marker", "previous", "manifest", "linked", "release_link"]
)
def test_packaged_recovery_keeps_edit_guard(interrupted_upgrade: dict, change: str) -> None:
    case = interrupted_upgrade
    if change == "widget":
        (case["plugin"] / "manifest.json").write_text("manual edit")
    elif change == "marker":
        (case["plugin"] / ".anolisa-omarchy-owned").write_text("../outside")
    elif change == "previous":
        (case["previous"] / "plugin/manifest.json").write_text("modified reference")
    elif change == "manifest":
        (case["previous"] / "bundle.json").write_text("{}")
    elif change == "linked":
        marker = case["plugin"] / ".anolisa-omarchy-owned"
        content = marker.read_bytes()
        marker.unlink()
        target = case["plugin"].parent / "linked-marker"
        target.write_bytes(content)
        marker.symlink_to(target)
    else:
        previous = case["previous"]
        moved = previous.parent.parent / "outside-release"
        previous.rename(moved)
        previous.symlink_to(moved, target_is_directory=True)
    before = case["actions"].read_bytes()
    result = case["run"](case["b"], "--recover")
    assert result.returncode != 0 and "Existing plugin differs" in result.stderr
    assert case["actions"].read_bytes() == before
    assert case["journal"].exists()
