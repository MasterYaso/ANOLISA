"""Select and recheck the Qoder executable before running it with enhancements."""

import hashlib
import os
import re
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from setup import read_json

VERSION = "1.1.84"
URL = (
    "https://qoder-ide.oss-accelerate.aliyuncs.com/qodercli/releases/"
    f"{VERSION}/qodercli-linux-x64-baseline.tar.gz"
)
ARCHIVE_SHA256 = "e85d82850c700b3e8691b7be35bf3c192223f8523ff22a96c011039a872f27a9"
BINARY_SHA256 = "c645b7aeceacee1ba118458811fc4bcf923920e5e13f9a8aad3404d143d46d31"
PAT = "QODER_PERSONAL_ACCESS_TOKEN"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def stage_qoder(cache: Path, destination: Path) -> None:
    """Publish only the verified native executable, including when repairing a release."""
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"qodercli-{VERSION}-linux-x64.tar.gz"
    if not archive.is_file() or digest(archive) != ARCHIVE_SHA256:
        with tempfile.TemporaryDirectory(dir=cache) as directory:
            temporary = Path(directory) / "qoder.tar.gz"
            with urllib.request.urlopen(URL, timeout=45) as response, temporary.open("wb") as out:
                shutil.copyfileobj(response, out)
            if digest(temporary) != ARCHIVE_SHA256:
                raise ValueError("Qoder CLI 下载文件校验失败。")
            temporary.replace(archive)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as directory:
        temporary = Path(directory) / "qodercli"
        with tarfile.open(archive) as tar:
            members = [
                entry
                for entry in tar.getmembers()
                if Path(entry.name).name == "qodercli" and entry.isfile()
            ]
            if len(members) != 1:
                raise ValueError("Qoder CLI 安装包中的程序文件无效。")
            with tar.extractfile(members[0]) as source, temporary.open("wb") as output:
                shutil.copyfileobj(source, output)
        if digest(temporary) != BINARY_SHA256:
            raise ValueError("Qoder CLI 程序校验失败。")
        temporary.chmod(0o755)
        temporary.replace(destination)


def inspect(path: Path, source: str) -> dict:
    report = {"source": source, "path": str(path), "version": None, "installation": "missing"}
    try:
        if not path.is_file() or not os.access(path, os.X_OK):
            return report
        path = path.resolve(strict=True)
        report.update(path=str(path), installation="unknown")
        checksum = digest(path)
        # The pinned digest identifies the tested build without starting Qoder for every check.
        if checksum != BINARY_SHA256:
            return dict(report, installation="incompatible")
        report.update(version=VERSION, installation="compatible", sha256=checksum)
    except OSError:
        pass
    return report


def candidates(prefix: Path) -> list[dict]:
    bundled = prefix / "bin/qodercli"
    reports = []
    managed = prefix.resolve().parent.parent
    for directory in os.get_exec_path():
        executable = shutil.which("qodercli", path=directory or ".")
        if executable:
            path = Path(executable).resolve()
            if (
                path == bundled.resolve()
                or path == (Path.home() / ".local/bin/anolisa-omarchy").resolve()
                or path.is_relative_to(managed / "releases")
            ):
                continue
            reports.append(inspect(path, "existing"))
            break
    return [*reports, inspect(bundled, "bundled")]


def selection(report: dict) -> dict:
    if report["installation"] != "compatible":
        raise ValueError("Qoder CLI 尚未通过兼容检查，请从设置重新安装。")
    path = report["path"] if report["source"] == "existing" else None
    return {
        "schema": 1,
        "source": report["source"],
        "path": path,
        "version": report["version"],
        "sha256": report["sha256"],
    }


def read_selection(config: Path) -> dict | None:
    selected = read_json(config / "agent.json")
    if selected is None:
        return None
    if selected.get("schema") != 1 or selected.get("source") not in ("existing", "bundled"):
        raise ValueError("Qoder 来源记录无效，请重新选择。")
    path = selected.get("path")
    if selected["source"] == "existing" and (
        not isinstance(path, str) or not Path(path).is_absolute()
    ):
        raise ValueError("Qoder 程序路径无效，请重新选择。")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(selected.get("version", ""))) or not re.fullmatch(
        r"[0-9a-f]{64}", str(selected.get("sha256", ""))
    ):
        raise ValueError("Qoder 兼容记录无效，请重新选择。")
    return selected


def executable(prefix: Path, selected: dict | None) -> Path:
    if selected and selected["source"] == "existing":
        return Path(selected["path"])
    return prefix / "bin/qodercli"


def validate(prefix: Path, selected: dict | None) -> dict:
    source = selected["source"] if selected else "bundled"
    path = executable(prefix, selected)
    report = inspect(path, source)
    if (
        selected
        and report["installation"] == "compatible"
        and (report["version"] != selected["version"] or report["sha256"] != selected["sha256"])
    ):
        report["installation"] = "incompatible"
    return report
