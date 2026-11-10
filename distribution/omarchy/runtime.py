#!/usr/bin/env python3
"""Desktop integration only; components retain their public CLI contracts."""

import argparse
import getpass
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import agent_installation as agents
import setup

APP_ID = "community.anolisa"
SERVICE = "anolisa-omarchy-security.service"
SERVICE_UNIT = Path("/etc/systemd/system") / SERVICE
SOCKET = "/run/anolisa-omarchy/sec-core.sock"
COSH_SETTINGS = "顶栏 ANOLISA → 设置 → 设置 cosh"
QODER_SETTINGS = "顶栏 ANOLISA → 设置 → 设置 Qoder"
COMPONENT_HELP = """ANOLISA - AI 助手 · 组件帮助

Qoder      读文件、执行命令和改代码。首页 → 用 Qoder 开始任务。
cosh       带 AI 的工作终端。首页 → 打开工作终端。用 /auth 配模型，用 /agent 提问。
Tokenless  精简 Qoder 的部分工具输出，减少发给模型的词元。首页 → Tokenless 看板。
sec-core   检查 Qoder 准备执行的 Bash 命令，记录发现的风险。首页 → sec-core 看板。

status 查看当前状态，doctor 排查安装和运行问题。"""


def locations() -> dict[str, Path]:
    """Keep credentials separate from the immutable application payload."""
    home = Path.home()
    return {
        "prefix": Path(__file__).absolute().parent,
        "config": Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "anolisa-omarchy",
        "state": Path(os.environ.get("XDG_STATE_HOME", home / ".local/state")) / "anolisa-omarchy",
        "run": Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
        / "anolisa-omarchy",
    }


def invoke(command: list[str], *, env: dict[str, str] | None = None) -> dict | list | None:
    """Return JSON only on success; never put component stderr in the bar process."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=6, env=env, check=False
        )
        if result.returncode == 0:
            value = json.loads(result.stdout)
            return value if isinstance(value, (dict, list)) else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return None


def environment(paths: dict[str, Path]) -> dict[str, str]:
    result = dict(os.environ)
    result["PATH"] = str(paths["prefix"] / "bin") + ":" + result.get("PATH", "")
    result["AGENT_SEC_DAEMON_SOCKET"] = SOCKET
    result["TOKENLESS_DATA_DIR"] = str(paths["state"] / "tokenless")
    # AW's provider and the dashboard must resolve the same store.
    result.pop("TOKENLESS_STATS_DB", None)
    return result


def credential_path(paths: dict[str, Path]) -> Path:
    return paths["config"] / "qoder-auth.json"


def read_credential(paths: dict[str, Path]) -> str | None:
    value = (setup.read_json(credential_path(paths)) or {}).get("token")
    return value if isinstance(value, str) and value.strip() else None


def authenticate(paths: dict[str, Path]) -> None:
    """Use a hidden prompt, not argv or a shell profile, for the Qoder PAT."""
    if not sys.stdin.isatty():
        raise ValueError("请在交互终端配置 Qoder PAT。")
    print("Qoder 认证：输入个人访问令牌（输入不回显，Ctrl+C 取消）。")
    setup.private_read(credential_path(paths))
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            token = getpass.getpass("Qoder PAT: ").strip()
        except getpass.GetPassWarning:
            raise ValueError("当前终端无法隐藏输入，请换一个交互终端。") from None
    if not token:
        raise ValueError("未输入令牌；没有更改现有认证。")
    setup.private_directory(paths["config"])
    setup.atomic_write(credential_path(paths), setup.json_bytes({"token": token}))
    print("认证已保存到当前用户的私有配置；未验证的令牌不表示认证成功。")


def aw_document(paths: dict[str, Path], qoder: Path | None = None) -> dict[str, Any]:
    prefix, state = paths["prefix"], paths["state"]
    security_argv = [
        str(prefix / "bin/aw-provider-sec-core"),
        "--cli",
        str(prefix / "bin/agent-sec-cli"),
        "--socket",
        "/run/anolisa-omarchy/sec-core.sock",
    ]
    token_argv = [
        str(prefix / "bin/aw-provider-tokenless"),
        "--cli",
        str(prefix / "bin/tokenless"),
        "--data-dir",
        str(state / "tokenless"),
    ]
    return {
        "apiVersion": "aw/v1alpha1",
        "kind": "AWConfiguration",
        "metadata": {"name": "omarchy-assistant"},
        "spec": {
            "daemon": {"startup": "on_demand", "endpoint": "auto", "state_dir": "auto"},
            "execution": {"guarantee": "native_hook", "default_event_budget_ms": 5000},
            "audit": {"enabled": True, "payload": "metadata_only"},
            "agents": {
                "qoder": {"adapter": "qoder", "argv": [str(qoder or prefix / "bin/qodercli")]}
            },
            "providers": {
                "security": {
                    "protocol": "aw-provider/v1alpha1",
                    "transport": {"type": "stdio", "location": "agent", "argv": security_argv},
                    "timeout_ms": 2000,
                    "max_output_bytes": 4096,
                    "config": {
                        "version": 1,
                        "mode": "block",
                        "unmapped_tool": "error",
                        "tools": {"Bash": {"language": "bash", "input_pointer": "/command"}},
                    },
                },
                "tokenless": {
                    "protocol": "aw-provider/v1alpha1",
                    "transport": {"type": "stdio", "location": "agent", "argv": token_argv},
                    "timeout_ms": 2000,
                    "max_output_bytes": 1048576,
                    "config": {"version": 1},
                    "view": {
                        "protocol": "aw-provider-view/v1alpha1",
                        "implementation": "tokenless",
                        "transport": {
                            "type": "stdio",
                            "location": "agent",
                            "argv": [token_argv[0], "--view", *token_argv[1:]],
                        },
                    },
                },
            },
            "events": {
                "tool.before": {
                    "enabled": True,
                    "required": True,
                    "steps": [
                        {
                            "id": "scan-code",
                            "match": {"tools": ["native:qoder:Bash"]},
                            "provider": "security",
                            "operation": "scan_code",
                            "effects": ["observe", "block"],
                            "on_error": "block",
                        },
                        {
                            "id": "rewrite-command",
                            "provider": "tokenless",
                            "operation": "pre_tool",
                            "effects": ["block"],
                            "on_error": "report",
                        },
                    ],
                },
                "tool.after": {
                    "enabled": True,
                    "required": True,
                    "steps": [
                        {
                            "id": "observe-completion",
                            "match": {"tools": ["native:qoder:Bash"]},
                            "provider": "security",
                            "operation": "observe_tool",
                            "effects": ["observe"],
                            "on_error": "report",
                        },
                        {
                            "id": "compress-result",
                            "provider": "tokenless",
                            "operation": "post_tool",
                            "effects": ["replace_result"],
                            "on_error": "report",
                        },
                    ],
                },
            },
        },
    }


def config_bytes(paths: dict[str, Path], selected: dict | None = None) -> bytes:
    return setup.json_bytes(aw_document(paths, agents.executable(paths["prefix"], selected)))


def check_managed_config(paths: dict[str, Path], selected: dict | None) -> bytes | None:
    config = paths["config"]
    current = setup.private_read(config / "aw.json")
    receipt = setup.read_json(config / "managed-config.json")
    expected = (
        config_bytes(paths, selected)
        if receipt is not None
        else (json.dumps(aw_document(paths), indent=2) + "\n").encode()
    )
    if current is not None and (
        current != expected
        or (
            receipt is not None
            and (
                receipt.get("schema") != 1
                or receipt.get("template") != "demo.3"
                or receipt.get("sha256") != hashlib.sha256(current).hexdigest()
            )
        )
    ):
        raise ValueError("Existing configuration differs (aw.json). Review before upgrading.")
    if current is None and receipt is not None:
        raise ValueError("Existing configuration differs (aw.json is missing).")
    return current


def configuration_plan(
    paths: dict[str, Path], probe_prefix: Path, choice: dict | None = None
) -> dict[Path, bytes]:
    config = paths["config"]
    selected = agents.read_selection(config)
    previous = check_managed_config(paths, selected)
    state = setup.read_state(config)
    plan = {}
    receipt = setup.read_json(config / "managed-config.json")
    if previous is not None and not receipt:
        backup = setup.private_read(config / "aw.demo2.json")
        if backup is not None and backup != previous:
            raise ValueError("Existing configuration differs (aw.demo2.json).")
        plan[config / "aw.demo2.json"] = previous
    old_selection = selected is not None and selected["version"] != agents.VERSION
    if choice is None and (selected is None or old_selection):
        candidate = next(
            (
                item
                for item in agents.candidates(probe_prefix)
                if item["installation"] == "compatible"
            ),
            None,
        )
        choice = agents.selection(candidate) if candidate else None
        if old_selection and choice is None:
            raise ValueError("升级后的 Qoder CLI 未通过兼容检查。")
    selected = choice or selected
    if selected is not None:
        plan[config / "agent.json"] = setup.json_bytes(selected)
    if setup.private_read(config / "setup.json") is None:
        if credential_path(paths).exists() or credential_path(paths).is_symlink():
            state["qoder"]["auth_mode"] = "pat"
        plan[config / "setup.json"] = setup.json_bytes(state)
    document = config_bytes(paths, selected)
    plan[config / "aw.json"] = document
    if not receipt or receipt.get("sha256") != hashlib.sha256(document).hexdigest():
        plan[config / "managed-config.json"] = setup.json_bytes(
            {
                "schema": 1,
                "template": "demo.3",
                "sha256": hashlib.sha256(document).hexdigest(),
                "previous_sha256": hashlib.sha256(previous).hexdigest() if previous else None,
            }
        )
    return plan


def write_plan(plan: dict[Path, bytes]) -> None:
    snapshots = {path: setup.private_read(path) for path in plan}
    changed = []
    try:
        for path, value in plan.items():
            if value == snapshots[path]:
                continue
            setup.atomic_write(path, value)
            changed.append(path)
    except BaseException:
        for path in reversed(changed):
            if snapshots[path] is None:
                path.unlink(missing_ok=True)
            else:
                setup.atomic_write(path, snapshots[path])
        raise


def configure(paths: dict[str, Path]) -> None:
    with setup.lock(paths["run"]):
        plan = configuration_plan(paths, paths["prefix"])
        for directory in ("config", "state"):
            setup.private_directory(paths[directory])
        write_plan(plan)


def auth_mode(paths: dict[str, Path], state: dict) -> str:
    return state["qoder"].get("auth_mode", "pat" if credential_path(paths).is_file() else "native")


def health(paths: dict[str, Path]) -> None:
    subprocess.run(["systemctl", "is-active", "--quiet", SERVICE], check=True, timeout=4)
    subprocess.run(
        [str(paths["prefix"] / "bin/agent-sec-daemon-health")],
        env=environment(paths),
        capture_output=True,
        check=True,
        timeout=4,
    )


def healthy(paths: dict[str, Path]) -> bool:
    try:
        health(paths)
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def verification(choice: dict) -> dict:
    record = choice.get("verification")
    if isinstance(record, dict) and record.get("result") in ("passed", "failed"):
        try:
            checked_at = datetime.fromisoformat(record["checked_at"]).isoformat(timespec="seconds")
        except (KeyError, ValueError, TypeError):
            pass
        else:
            return {"result": record["result"], "checked_at": checked_at, "method": "user_reported"}
    return {"result": "not_run", "checked_at": None, "method": None}


def dashboards(paths: dict[str, Path], now: str) -> tuple[dict, dict]:
    prefix = paths["prefix"]
    env = environment(paths)
    events = invoke(
        [
            str(prefix / "bin/agent-sec-cli"),
            "events",
            "--output",
            "json",
            "--limit",
            "200",
            "--category",
            "code_scan",
        ],
        env=env,
    )
    security = {
        "available": isinstance(events, list) and all(isinstance(item, dict) for item in events),
        "checked": None,
        "risks": None,
        "blocked": None,
        "scope": "recent_service_code_scans",
        "limit": 200,
        "sampled_at": now,
    }
    if security["available"]:
        findings = []
        for item in events[:200]:
            if item.get("result") != "succeeded":
                continue
            details = item.get("details")
            result = details.get("result") if isinstance(details, dict) else None
            if isinstance(result, dict) and result.get("verdict") in ("warn", "deny"):
                recorded = item.get("timestamp")
                try:
                    recorded = datetime.fromisoformat(recorded).isoformat(timespec="seconds")
                except (ValueError, TypeError):
                    recorded = None
                findings.append({"verdict": result["verdict"], "timestamp": recorded})
        security.update(
            checked=min(len(events), 200), risks=len(findings), recent_risks=findings[:5]
        )
    store = paths["state"] / "tokenless/stats.db"
    tokens = {
        "available": False,
        "saved": None,
        "before": None,
        "after": None,
        "records": None,
        "scope": "recent_managed_user_records",
        "limit": 200,
        "sampled_at": now,
        "state": "empty" if not store.is_file() else "unavailable",
    }
    if store.is_file():
        response = invoke(
            [str(prefix / "bin/tokenless"), "stats", "summary", "--json", "--limit", "200"], env=env
        )
        if isinstance(response, dict) and response.get("schema_version") == "1.1":
            total = response.get("total")
            fields = {
                "saved": "tokens_saved",
                "before": "before_tokens",
                "after": "after_tokens",
                "records": "records",
            }
            if isinstance(total, dict) and all(
                type(total.get(field)) is int and total[field] >= 0 for field in fields.values()
            ):
                tokens.update({key: total[field] for key, field in fields.items()})
                tokens.update(available=True, state="observed" if tokens["records"] else "empty")
    return security, tokens


def status(paths: dict[str, Path], *, diagnostic: bool = False) -> dict[str, Any]:
    issues = []
    config = paths["config"]
    state = setup.read_state(config)
    selected = None
    try:
        selected = agents.read_selection(config)
        qoder = agents.validate(paths["prefix"], selected)
    except (OSError, ValueError):
        qoder = {"source": "unknown", "installation": "unknown", "version": None}
        issues.append("qoder_selection")
    mode = auth_mode(paths, state)
    pat = False
    try:
        pat = bool(os.environ.get(agents.PAT) or read_credential(paths))
    except (OSError, ValueError):
        issues.append("qoder_credential")
    try:
        configured = check_managed_config(paths, selected) is not None
    except (OSError, ValueError):
        configured = False
    if not configured:
        issues.append("configuration")
    service_ready = healthy(paths)
    if not service_ready:
        issues.append("security_service")
    if qoder["installation"] != "compatible":
        issues.append("qoder_installation")
    security, tokens = dashboards(paths, timestamp())
    if not security["available"]:
        issues.append("security_records")
    if tokens["state"] == "unavailable":
        issues.append("tokenless_records")
    cosh_path = paths["prefix"] / "bin/cosh"
    cosh_present = cosh_path.is_file() and os.access(cosh_path, os.X_OK)
    if not cosh_present:
        issues.append("cosh_installation")
    qoder.update(
        choice=state["qoder"]["choice"],
        auth_mode=mode,
        verification=verification(state["qoder"]),
        configuration=("present" if pat else "missing") if mode == "pat" else "unknown",
        enhancement="configured" if service_ready and configured else "unavailable",
    )
    if not diagnostic:
        qoder.pop("path", None)
        qoder.pop("sha256", None)
    else:
        qoder["candidates"] = agents.candidates(paths["prefix"])
    report = {
        "schema_version": 2,
        "ok": True,
        "authConfigured": pat,
        "setup": {
            "needs_prompt": not state["deferred"]
            and any(state[key]["choice"] == "pending" for key in ("cosh", "qoder")),
            "deferred": state["deferred"],
            "running": setup.running(paths["run"]),
        },
        "cosh": {
            "installation": "compatible" if cosh_present else "missing",
            "choice": state["cosh"]["choice"],
            "configuration": "unknown",
            "reported_configured": state["cosh"].get("reported_configured") is True,
            "verification": verification(state["cosh"]),
        },
        "qoder": qoder,
        "security": security,
        "tokenless": tokens,
        "issues": issues,
    }
    if diagnostic:
        report["dependency_tools"] = {
            name: shutil.which(name) is not None
            for name in (
                "omarchy",
                "omarchy-shell",
                "omarchy-launch-terminal",
                "systemctl",
                "sudo",
                "ldd",
            )
        }
        try:
            manifest = json.loads((paths["prefix"] / "bundle.json").read_text())
            report["bundled_components"] = manifest["components"]
        except (OSError, ValueError, KeyError):
            report["bundled_components"] = None
    return report


def component_states(paths: dict[str, Path], report: dict[str, Any]) -> dict[str, tuple[str, str]]:
    binary = paths["prefix"] / "bin"
    issues = report["issues"]

    def executable(name: str) -> bool:
        path = binary / name
        return path.is_file() and os.access(path, os.X_OK)

    qoder = report["qoder"]
    qoder_installation = {
        "compatible": "已安装",
        "incompatible": "版本不兼容",
        "missing": "未安装",
    }.get(qoder["installation"], "安装状态待确认")
    if qoder["installation"] != "compatible":
        qoder_state = "请检查程序选择"
    elif qoder["configuration"] == "missing":
        qoder_state = "待填写 PAT"
    elif qoder["choice"] in ("pending", "skipped"):
        qoder_state = "待设置"
    elif qoder["verification"]["result"] == "passed":
        qoder_state = "上次连接检查通过"
    elif qoder["verification"]["result"] == "failed":
        qoder_state = "连接检查未通过"
    elif qoder["configuration"] == "present":
        qoder_state = "PAT 已配置，连接待验证"
    else:
        qoder_state = "登录状态待确认"

    cosh = report["cosh"]
    cosh_installed = cosh["installation"] == "compatible"
    cosh_state = "待配置模型"
    if not cosh_installed:
        cosh_state = "请重新安装"
    elif cosh["verification"]["result"] == "passed":
        cosh_state = "上次连接检查通过"
    elif cosh["verification"]["result"] == "failed":
        cosh_state = "连接检查未通过"
    elif cosh["reported_configured"]:
        cosh_state = "模型已配置，连接待验证"
    elif cosh["choice"] == "configure":
        cosh_state = "模型配置待确认"

    tokens_installed = executable("tokenless")
    provider_installed = executable("aw-provider-tokenless")
    if not tokens_installed or not provider_installed:
        tokens_state = "程序文件不全，请重新安装"
    elif "configuration" in issues:
        tokens_state = "待接入"
    else:
        tokens_state = {
            "observed": "已接入，已有处理记录",
            "empty": "已接入，暂无处理记录",
        }.get(report["tokenless"]["state"], "已接入，统计暂不可读")

    security_installed = executable("agent-sec-cli") and executable("agent-sec-daemon")
    if not security_installed or not SERVICE_UNIT.is_file():
        security_state = "服务未安装"
    elif "security_service" not in issues:
        security_state = "服务运行中"
    else:
        try:
            active = (
                subprocess.run(
                    ["systemctl", "is-active", "--quiet", SERVICE], check=False, timeout=4
                ).returncode
                == 0
            )
        except (OSError, subprocess.SubprocessError):
            active = False
        security_state = "服务健康检查未通过" if active else "服务未运行"

    return {
        "Qoder": (qoder_installation, qoder_state),
        "cosh": ("已安装" if cosh_installed else "未安装", cosh_state),
        "Tokenless": ("已安装" if tokens_installed else "未安装", tokens_state),
        "sec-core": ("已安装" if security_installed else "未安装", security_state),
    }


def print_status(paths: dict[str, Path], report: dict[str, Any], *, diagnostic: bool) -> None:
    rows = component_states(paths, report)
    if diagnostic:
        issues = set(report["issues"])
        security_state = rows["sec-core"][1]
        checks = {
            "qoder_selection": ("Qoder", "程序选择无法读取", "在设置中重新选择 Qoder 程序"),
            "qoder_credential": ("Qoder", "PAT 配置无法读取", "重新配置 Qoder PAT"),
            "configuration": ("Qoder 增强", "受管配置缺失或已修改", "重新运行安装器并检查提示"),
            "qoder_installation": ("Qoder", rows["Qoder"][0], "在设置中选择可用程序"),
            "cosh_installation": ("cosh", "程序未安装", "重新运行安装器"),
            "security_service": ("sec-core", security_state, "重新运行安装器并检查服务日志"),
            "security_records": ("sec-core", "扫描记录无法读取", "检查安全服务日志"),
            "tokenless_records": ("Tokenless", "处理记录无法读取", "打开 Tokenless 看板查看详情"),
        }
        if "qoder_selection" in issues:
            issues.discard("qoder_installation")
        if "security_service" in issues:
            issues.discard("security_records")
        problems = [checks[issue] for issue in checks if issue in issues]
        if report["qoder"]["configuration"] == "missing" and "qoder_credential" not in issues:
            problems.append(("Qoder", "尚未填写 PAT", "在设置中填写令牌或切换到 Qoder CLI 登录"))
        if rows["Tokenless"][1] == "程序文件不全，请重新安装":
            problems.append(("Tokenless", "程序文件不全", "重新运行安装器"))
        if security_state == "服务未安装" and "security_service" not in issues:
            problems.append(("sec-core", security_state, "重新运行安装器"))
        if problems:
            for name, reason, next_step in problems:
                print(f"{name}  {reason}。{next_step}。")
        else:
            print("未发现安装或运行问题。")
        return

    try:
        metadata = json.loads((paths["prefix"] / "bundle.json").read_text())
        version = metadata.get("version", "") if isinstance(metadata, dict) else ""
    except (OSError, ValueError):
        version = ""
    print(f"ANOLISA - AI 助手 {version}".rstrip())
    print("\n组件        安装状态    当前状态")
    for name, (installation, state) in rows.items():
        print(f"{name:<12}{installation}    {state}")
    if report["setup"]["needs_prompt"]:
        print("\n下一步  从顶栏打开 ANOLISA - AI 助手，点击「开始设置」。")


def run_agent(
    paths: dict[str, Path], arguments: list[str], native_settings: Path | None = None
) -> int:
    health(paths)
    config = paths["config"]
    with setup.lock(paths["run"]):
        state = setup.read_state(config)
        selected = agents.read_selection(config)
        report = agents.validate(paths["prefix"], selected)
        if report["installation"] != "compatible":
            raise ValueError("Qoder 程序不可用或已变更，请在设置中重新选择。")
        if check_managed_config(paths, selected) is None:
            raise ValueError("安装配置缺失，请重新运行安装程序。")
        env = environment(paths)
        if auth_mode(paths, state) == "pat":
            token = env.get(agents.PAT) or read_credential(paths)
            if not token:
                raise ValueError("请在设置中补充 Qoder PAT 或切换到原生登录。")
            env[agents.PAT] = token
        else:
            env.pop(agents.PAT, None)
        stable = dict(paths, prefix=paths["prefix"].resolve())
        document = setup.json_bytes(aw_document(stable, Path(report["path"])))
        run_config = paths["run"] / (hashlib.sha256(document).hexdigest() + ".json")
        if setup.private_read(run_config) != document:
            setup.atomic_write(run_config, document)
    command = [
        str(stable["prefix"] / "bin/aw"),
        "run",
        "--config",
        str(run_config),
        "--agent",
        "qoder",
    ]
    if report["source"] == "bundled":
        settings = json.loads(native_settings.read_text()) if native_settings else {}
        if not isinstance(settings, dict) or not isinstance(settings.get("general", {}), dict):
            raise ValueError("Qoder 设置需要使用 JSON 对象。")
        settings.setdefault("general", {})["enableAutoUpdate"] = False
        with tempfile.TemporaryDirectory(dir=paths["run"]) as directory:
            overlay = Path(directory) / "settings.json"
            setup.atomic_write(overlay, setup.json_bytes(settings))
            return subprocess.call(
                [*command, "--native-settings", str(overlay), "--", *arguments], env=env
            )
    if native_settings is not None:
        command += ["--native-settings", str(native_settings.resolve(strict=True))]
    return subprocess.call([*command, "--", *arguments], env=env)


def run_cosh(paths: dict[str, Path], arguments: list[str]) -> int:
    print("cosh：输入 /auth 配置模型，/status 查看状态。", flush=True)
    print("单独输入 /agent 回车，再在 ◆ 后写问题并回车。Esc 返回 shell，exit 退出。", flush=True)
    env = environment(paths)
    env.pop(agents.PAT, None)
    # Mise's missing-command handler takes precedence over cosh's natural-language routing.
    env["MISE_NOT_FOUND_AUTO_INSTALL"] = "0"
    return subprocess.call([str(paths["prefix"] / "bin/cosh"), *arguments], env=env)


def skip_qoder(paths: dict[str, Path], state: dict) -> None:
    state["qoder"]["choice"] = "skipped"
    setup.save_state(paths["config"], state)
    print(f"已跳过 Qoder 设置。之后可从{QODER_SETTINGS}继续。")


def choose_qoder(paths: dict[str, Path], state: dict) -> bool:
    candidates = agents.candidates(paths["prefix"])
    usable = [item for item in candidates if item["installation"] == "compatible"]
    if not usable:
        if any(item["source"] == "existing" for item in candidates):
            print("检测到本机 Qoder CLI，当前程序未通过插件兼容检查。")
        print(f"未检测到可用的 Qoder CLI。现在安装 {agents.VERSION} 吗？")
        answer = input("输入 1 安装，或直接按 Enter 跳过 ").strip()
        if not answer:
            skip_qoder(paths, state)
            return False
        if answer != "1":
            raise ValueError("请输入 1 安装，或按 Enter 跳过。")
        print(f"正在安装 Qoder CLI {agents.VERSION}…", flush=True)
        with tempfile.TemporaryDirectory(dir=paths["run"]) as directory:
            agents.stage_qoder(Path(directory), paths["prefix"].resolve() / "bin/qodercli")
        candidate = agents.validate(paths["prefix"], None)
        if candidate["installation"] != "compatible":
            raise ValueError("安装后的 Qoder CLI 未通过校验。")
        usable = [candidate]
        print(f"Qoder CLI {candidate['version']} 已安装，接下来配置账户信息。")
    else:
        print("已检测到 Qoder CLI，接下来配置账户信息。")
    current = agents.read_selection(paths["config"])
    selected = next((item for item in usable if agents.selection(item) == current), usable[0])
    plan = configuration_plan(paths, paths["prefix"], agents.selection(selected))
    existing_mode = auth_mode(paths, state)
    default_mode = "2" if existing_mode == "pat" else "1"
    print(
        "\n在哪里配置 Qoder 账户信息？\n\n"
        "1. 在 Qoder CLI 中配置\n"
        "   打开 Qoder 后，按提示用浏览器或 PAT 完成认证。\n\n"
        "2. 直接输入 Qoder PAT\n"
        "   在这里粘贴令牌。插件会保存它，以后打开 Qoder 时自动使用。\n\n"
        "3. 稍后设置"
    )
    mode = input(f"请选择 [默认 {default_mode}] ").strip().lower()
    if mode == "3":
        skip_qoder(paths, state)
        return False
    mode = mode or default_mode
    if mode not in ("1", "2"):
        raise ValueError("无效的认证选项。")
    if mode == "2":
        if os.environ.get(agents.PAT) or read_credential(paths):
            print("将使用现有的 Qoder PAT。")
        else:
            authenticate(paths)
    state["qoder"] = {"choice": "configure", "auth_mode": "native" if mode == "1" else "pat"}
    plan[paths["config"] / "setup.json"] = setup.json_bytes(state)
    setup.private_directory(paths["config"])
    write_plan(plan)
    return mode == "1"


def wizard(paths: dict[str, Path], component: str | None, *, defer: bool = False) -> None:
    with setup.lock(paths["run"]):
        state = setup.read_state(paths["config"])
        if defer:
            state["deferred"] = True
            setup.save_state(paths["config"], state)
            return
        if not sys.stdin.isatty():
            raise ValueError("请在交互终端运行设置。")
        print("ANOLISA - AI 助手\ncosh 和 Qoder 可以分别配置，也可以稍后设置。")
        open_qoder = False
        for name in (component,) if component else ("cosh", "qoder"):
            if component is None and state[name]["choice"] != "pending":
                continue
            try:
                if name == "qoder":
                    if component is None:
                        cosh = state["cosh"]
                        if cosh.get("reported_configured"):
                            print("cosh 配置已完成。接下来要配置 Qoder 吗？")
                        elif cosh["choice"] == "skipped":
                            print("已跳过 cosh。接下来要配置 Qoder 吗？")
                        else:
                            print("cosh 配置待完成。接下来要配置 Qoder 吗？")
                        print(f"直接按 Enter 跳过。之后可从{QODER_SETTINGS}继续。")
                        answer = input("输入 1 继续配置 Qoder ").strip()
                        if not answer:
                            skip_qoder(paths, state)
                            continue
                        if answer != "1":
                            raise ValueError("请输入 1 继续，或按 Enter 跳过。")
                    open_qoder = choose_qoder(paths, state)
                else:
                    print(f"配置 cosh 工作终端。之后可从{COSH_SETTINGS}继续。")
                    answer = input("输入 1 开始配置，或直接按 Enter 跳过 ").strip()
                    if answer not in ("", "1"):
                        raise ValueError("无效的 cosh 选项。")
                    if answer:
                        print("进入 cosh 后，输入 /auth 配置模型。")
                        print("配置完成后，输入 exit 返回此向导。")
                        input("按 Enter 打开 cosh 进行配置 ")
                        if run_cosh(paths, []) != 0:
                            raise ValueError("cosh 退出异常。")
                        confirmed = input("已在 cosh 配置模型？[y/N] ").strip().lower() == "y"
                        state["cosh"] = {"choice": "configure", "reported_configured": confirmed}
                    else:
                        state["cosh"]["choice"] = "skipped"
                    setup.save_state(paths["config"], state)
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                location = COSH_SETTINGS if name == "cosh" else QODER_SETTINGS
                print(f"{name} 设置未完成。{error}\n之后可从{location}重试。")
        labels = {"pending": "待设置", "configure": "已处理，连接待验证", "skipped": "已跳过"}
        final = setup.read_state(paths["config"])
        for name in ("cosh", "qoder"):
            print(f"{name}  {labels[final[name]['choice']]}")
        check = (
            "2" if open_qoder else input("可选检查：1 打开 cosh，2 打开 Qoder，回车结束：").strip()
        )
    if check in ("1", "2"):
        name = "cosh" if check == "1" else "qoder"
        if open_qoder:
            print("正在打开 Qoder CLI。用 /login 配置账户，完成后输入 exit 返回向导。")
        else:
            print("请发送一个简单问题，看到结果后输入 exit 回到向导。")
        code = run_cosh(paths, []) if name == "cosh" else run_agent(paths, [])
        answer = input("收到真实回答？[y 已收到 / n 失败 / 回车跳过记录] ").strip().lower()
        if answer in ("y", "n"):
            with setup.lock(paths["run"]):
                latest = setup.read_state(paths["config"])
                if latest[name] != final[name]:
                    raise ValueError("检查期间配置已改变，请重新检查。")
                latest[name]["verification"] = {
                    "result": "passed" if code == 0 and answer == "y" else "failed",
                    "checked_at": timestamp(),
                }
                setup.save_state(paths["config"], latest)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="anolisa-omarchy",
        description="ANOLISA - AI 助手。运行 anolisa-omarchy help 查看组件用途和使用入口。",
    )
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("help", help="介绍组件用途和使用入口")
    for action in ("cosh", "auth", "configure", "security", "tokens"):
        actions.add_parser(action)
    for action in ("status", "doctor"):
        actions.add_parser(action).add_argument("--json", action="store_true")
    for action in ("setup", "settings"):
        group = actions.add_parser(action).add_mutually_exclusive_group()
        group.add_argument("--component", choices=("cosh", "qoder"))
        group.add_argument("--defer", action="store_true")
    actions.add_parser("qoder").add_argument("--native-settings", type=Path)
    arguments = sys.argv[1:]
    forwarded = []
    if "--" in arguments:
        split = arguments.index("--")
        arguments, forwarded = arguments[:split], arguments[split + 1 :]
    options = parser.parse_args(arguments)
    action = options.action
    if forwarded and action not in ("cosh", "qoder"):
        parser.error("Only cosh and qoder accept forwarded arguments")
    paths = locations()
    if action == "help":
        print(COMPONENT_HELP)
    elif action == "configure":
        configure(paths)
    elif action == "auth":
        with setup.lock(paths["run"]):
            state = setup.read_state(paths["config"])
            authenticate(paths)
            state["qoder"] = {"choice": "configure", "auth_mode": "pat"}
            setup.save_state(paths["config"], state)
    elif action == "qoder":
        try:
            return run_agent(paths, forwarded, options.native_settings)
        except (OSError, subprocess.SubprocessError):
            print("安全检查服务不可用，请运行诊断并修复后重试。", file=sys.stderr)
            if sys.stdin.isatty():
                input("按 Enter 关闭。")
            return 1
    elif action == "cosh":
        return run_cosh(paths, forwarded)
    elif action in ("setup", "settings"):
        wizard(paths, options.component, defer=options.defer)
    elif action in ("status", "doctor"):
        report = status(paths, diagnostic=action == "doctor")
        if options.json:
            print(json.dumps(report, ensure_ascii=False))
        else:
            print_status(paths, report, diagnostic=action == "doctor")
        if action == "doctor" and not options.json and sys.stdin.isatty():
            input("按 Enter 关闭。")
    else:
        command = (
            [str(paths["prefix"] / "bin/agent-sec-cli"), "events", "--limit", "50"]
            if action == "security"
            else [str(paths["prefix"] / "bin/tokenless"), "stats", "summary", "--limit", "200"]
        )
        subprocess.run(command, env=environment(paths), check=False)
        if sys.stdin.isatty():
            input("按 Enter 关闭。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print("\n已取消。", file=sys.stderr)
        raise SystemExit(130) from None
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"ANOLISA: {error}", file=sys.stderr)
        raise SystemExit(1) from None
