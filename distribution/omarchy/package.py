#!/usr/bin/env python3
"""Assemble a portable Omarchy candidate from already built ANOLISA binaries."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
from pathlib import Path

import agent_installation as agents

VERSION = "0.1.1"
DEMO2_SHA256 = "3c340d0ef76fd218f4e5fd689db83d3181a63e506bc9a9c9b238cfb756a5f022"
MODULES = ("runtime.py", "setup.py", "agent_installation.py", "system_install.py")


def digest(filename: Path) -> str:
    with filename.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def archive_permissions(info: tarfile.TarInfo) -> tarfile.TarInfo:
    """Do not inherit permissive DrvFS modes from a Windows-hosted checkout."""
    private_binary = info.name.rsplit("/", 1)[-1] in ("cosh-core", "cosh-shell", "cosh-gateway")
    executable = info.name.endswith("/install") or "/payload/bin/" in info.name or private_binary
    info.mode = 0o755 if info.isdir() or executable else 0o644
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def reuse_payload(archive: Path, payload: Path) -> dict:
    checksum = digest(archive)
    if checksum != DEMO2_SHA256:
        raise ValueError("The demo.2 archive does not match the validated baseline")
    base = "anolisa-omarchy-0.1.0-demo.2"
    prefix = base + "/payload/"
    with tarfile.open(archive) as tar:
        metadata = json.load(tar.extractfile(f"{base}/bundle.json"))
        for entry in tar.getmembers():
            if not entry.name.startswith(prefix) or not entry.isfile():
                continue
            relative = entry.name.removeprefix(prefix)
            if (
                not relative.startswith(("bin/", "libexec/", "share/"))
                or relative == "bin/qodercli"
            ):
                continue
            target = payload / relative
            if not target.resolve().is_relative_to(payload.resolve()):
                raise ValueError("Unexpected payload path")
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(entry) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            if digest(target) != metadata["files"][relative]:
                raise ValueError(f"Reused payload digest mismatch: {relative}")
            target.chmod(entry.mode)
    return {
        "kind": "verified_demo2_archive",
        "archive_sha256": checksum,
        "component_commit": metadata["source_commit"],
        "original_build": "Ubuntu 24.04 on WSL, Linux x86_64, Rust 1.97.1",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--bin-dir", type=Path)
    source.add_argument("--reuse-demo2", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path)
    options = parser.parse_args()
    here = Path(__file__).resolve().parent
    repo = here.parents[1]
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    stage = output / f"anolisa-omarchy-{VERSION}"
    if stage.exists():
        raise ValueError(f"Output already exists; use a new output directory: {stage}")
    stage.mkdir()
    payload = stage / "payload"
    payload.mkdir()
    if options.reuse_demo2:
        provenance = reuse_payload(options.reuse_demo2, payload)
    else:
        if options.cache is None:
            parser.error("--bin-dir requires --cache")
        binaries = options.bin_dir.resolve()
        env = dict(os.environ, BIN_DIR=str(binaries), DESTDIR=str(payload))
        subprocess.run(
            ["bash", str(repo / "src/cosh-ng/packaging/raw/package.sh"), "stage"],
            env=env,
            check=True,
        )
        bindir = payload / "bin"
        for name in (
            "aw",
            "aw-provider-sec-core",
            "aw-provider-tokenless",
            "agent-sec-cli",
            "agent-sec-daemon",
            "agent-sec-daemon-health",
            "tokenless",
        ):
            shutil.copy2(binaries / name, bindir / name)
            (bindir / name).chmod(0o755)
        provenance = {"kind": "provided_linux_build_outputs"}
    agents.stage_qoder(options.cache or output / "downloads", payload / "bin/qodercli")
    shutil.copytree(
        here / "plugin", payload / "plugin", ignore=shutil.ignore_patterns("__pycache__")
    )
    for name in MODULES:
        shutil.copy2(here / name, payload)
    for name in (
        "install",
        "install.py",
        "README.md",
        "README_zh.md",
        "BUILDING.md",
        "USER_GUIDE.md",
        "USER_GUIDE_zh.md",
    ):
        shutil.copy2(here / name, stage / name)
    for filename in ("README.md", "README_zh.md"):
        target = stage / filename
        target.write_text(target.read_text().replace("../../LICENSE", "LICENSE"))
    shutil.copy2(repo / "LICENSE", stage / "LICENSE")
    (stage / "install").chmod(0o755)
    licenses = payload / "share/licenses/anolisa-omarchy"
    licenses.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo / "LICENSE", licenses / "ANOLISA-APACHE-2.0")
    if not options.reuse_demo2:
        shutil.copy2(repo / "src/tokenless/third_party/rtk/LICENSE", licenses / "RTK-MIT")
    commit = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    files = {
        path.relative_to(payload).as_posix(): digest(path)
        for path in sorted(payload.rglob("*"))
        if path.is_file()
    }
    manifest = {
        "schema": 1,
        "version": VERSION,
        "platform": "linux-x86_64",
        "source_commit": commit,
        "binary_provenance": provenance,
        "assembly": {"platform": platform.platform(), "python": platform.python_version()},
        "integration_source": {
            path.relative_to(repo).as_posix(): digest(path)
            for path in sorted(here.rglob("*"))
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.name not in ("bundle.json", "SHA256SUMS")
        },
        "files": files,
        "components": {
            "cosh-ng": "0.28.1",
            "sec-core": "1.1.2",
            "tokenless": "0.9.2",
            "aw": "0.1.0",
            "qodercli": agents.VERSION,
        },
        "downloads": [{"name": "Qoder CLI", "url": agents.URL, "sha256": agents.ARCHIVE_SHA256}],
        "notice": "Experimental integration; Qoder remains subject to its own terms.",
    }
    (stage / "bundle.json").write_text(json.dumps(manifest, indent=2) + "\n")
    archive = output / f"{stage.name}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(stage, arcname=stage.name, filter=archive_permissions)
    (output / "SHA256SUMS").write_text(f"{digest(archive)}  {archive.name}\n")
    print(archive)


if __name__ == "__main__":
    main()
