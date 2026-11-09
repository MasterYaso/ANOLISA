"""Check the readable CLI without depending on a desktop or a model account."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_demo3 import inputs, program
from test_integration import load
from test_integration import paths as paths


def test_help_without_configuration(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    runtime = load("runtime")
    monkeypatch.setattr(sys, "argv", ["anolisa-omarchy", "help"])
    assert runtime.main() == 0
    output = capsys.readouterr().out
    for label in ("Qoder", "cosh", "Tokenless", "sec-core", "/auth", "/agent"):
        assert label in output
    monkeypatch.setattr(sys, "argv", ["anolisa-omarchy", "--help"])
    with pytest.raises(SystemExit) as error:
        runtime.main()
    assert error.value.code == 0
    assert "anolisa-omarchy help" in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["1", "2"])
def test_qoder_auth_choice(
    paths: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    mode: str,
) -> None:
    runtime = load("runtime")
    program(runtime.agents, paths["prefix"], monkeypatch)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.delenv(runtime.agents.PAT, raising=False)
    monkeypatch.setattr(runtime.getpass, "getpass", lambda _prompt: "synthetic-demo4-pat")
    launches = []
    monkeypatch.setattr(runtime, "run_agent", lambda *args: launches.append(args) or 0)
    inputs(monkeypatch, [mode, ""])
    runtime.wizard(paths, "qoder")
    output = capsys.readouterr().out
    assert "在哪里配置 Qoder 账户信息？" in output
    assert "按提示用浏览器或 PAT 完成认证" in output
    assert "直接输入 Qoder PAT" in output
    assert "3. 稍后设置" in output
    assert "synthetic-demo4-pat" not in output
    state = runtime.setup.read_state(paths["config"])
    if mode == "1":
        assert state["qoder"]["auth_mode"] == "native"
        assert "正在打开 Qoder CLI" in output and len(launches) == 1
        assert runtime.read_credential(paths) is None
    else:
        assert not launches
        assert state["qoder"]["auth_mode"] == "pat"
        assert runtime.read_credential(paths) == "synthetic-demo4-pat"
        assert runtime.credential_path(paths).stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("answer", ["", "1"])
def test_missing_qoder_offers_install(
    paths: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    answer: str,
) -> None:
    runtime = load("runtime")
    binary = program(runtime.agents, paths["prefix"], monkeypatch)
    data = binary.read_bytes()
    binary.unlink()
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    installed = []

    def stage_qoder(_cache: Path, destination: Path) -> None:
        installed.append(destination)
        destination.write_bytes(data)
        destination.chmod(0o755)

    monkeypatch.setattr(runtime.agents, "stage_qoder", stage_qoder)
    inputs(monkeypatch, ["1", "3", ""] if answer else ["", ""])
    runtime.wizard(paths, "qoder")
    output = capsys.readouterr().out
    assert "未检测到可用的 Qoder CLI" in output
    assert "设置 → 设置 Qoder" in output
    assert installed == ([binary] if answer else [])
    assert ("接下来配置账户信息" in output) == bool(answer)


def test_upgrade_replaces_old_program_record(
    paths: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = load("runtime")
    program(runtime.agents, paths["prefix"], monkeypatch)
    old = {
        "schema": 1,
        "source": "existing",
        "path": "/opt/old/qodercli",
        "version": "1.1.71",
        "sha256": "a" * 64,
    }
    runtime.configure(paths)
    runtime.write_plan(runtime.configuration_plan(paths, paths["prefix"], old))
    runtime.setup.atomic_write(runtime.credential_path(paths), b'{"token":"fixture"}')
    plan = runtime.configuration_plan(paths, paths["prefix"])
    runtime.write_plan(plan)
    selected = runtime.agents.read_selection(paths["config"])
    assert selected["version"] == "1.1.84" and selected["source"] == "bundled"
    assert runtime.read_credential(paths) == "fixture"


def test_human_report_preserves_json(
    paths: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    runtime = load("runtime")
    program(runtime.agents, paths["prefix"], monkeypatch)
    meta = paths["prefix"] / "bundle.json"
    meta.write_text(json.dumps(dict(json.loads(meta.read_text()), version="0.1.0-demo.4")))
    for name in ("cosh", "tokenless", "aw-provider-tokenless", "agent-sec-cli", "agent-sec-daemon"):
        binary = paths["prefix"] / "bin" / name
        binary.touch(mode=0o755)
    service = paths["prefix"] / "test.service"
    service.touch()
    monkeypatch.setattr(runtime, "SERVICE_UNIT", service)
    monkeypatch.setattr(runtime, "locations", lambda: paths)
    monkeypatch.setattr(runtime, "healthy", lambda _paths: True)
    monkeypatch.setattr(runtime, "invoke", lambda *args, **kwargs: [])
    runtime.configure(paths)
    monkeypatch.setattr(sys, "argv", ["anolisa-omarchy", "status"])
    assert runtime.main() == 0
    output = capsys.readouterr().out
    for text in ("0.1.0-demo.4", "待设置", "待配置模型", "暂无处理记录", "服务运行中"):
        assert text in output
    monkeypatch.setattr(sys, "argv", ["anolisa-omarchy", "status", "--json"])
    assert runtime.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == 2 and report["ok"] and report["issues"] == []
    assert report["qoder"]["configuration"] == "unknown"
    assert report["tokenless"]["state"] == "empty"
    monkeypatch.setattr(sys, "argv", ["anolisa-omarchy", "doctor"])
    assert runtime.main() == 0
    assert capsys.readouterr().out == "未发现安装或运行问题。\n"

    monkeypatch.setattr(runtime, "healthy", lambda _paths: False)
    run = runtime.subprocess.run
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda command, **kwargs: (
            subprocess.CompletedProcess(command, 3)
            if command[0] == "systemctl"
            else run(command, **kwargs)
        ),
    )
    assert runtime.main() == 0
    assert capsys.readouterr().out == "sec-core  服务未运行。重新运行安装器并检查服务日志。\n"
