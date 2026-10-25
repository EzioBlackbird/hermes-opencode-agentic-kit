#!/usr/bin/env python3
"""
One-Click Cross-Machine Bootstrapper for Hermes + OpenCode Agentic Kit
(Gated Project Orchestration + REA Reverse Engineer Anything + CLI-Anything / CLI-Hub)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

REA_PACKAGE = "rea-agents@6.8.0"
GHIDRA_URL = "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.1.4_build/ghidra_12.1.4_PUBLIC_20260921.zip"
JADX_URL = "https://github.com/1013503897/jadx-headless-mcp/releases/download/v0.7.1/jadx-headless-mcp-0.7.1-all.jar"
JADX_SHA256 = "6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75"
APKTOOL_URL = (
    "https://github.com/iBotPeaches/Apktool/releases/download/v3.0.3/apktool_3.0.3.jar"
)
JDK21_API = "https://api.adoptium.net/v3/assets/latest/21/hotspot?architecture=x64&image_type=jdk&os=windows&vendor=eclipse"


def log(msg: str) -> None:
    print(f"[bootstrap] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    log(f"Downloading {url} -> {dest}")
    req = urllib.request.Request(
        url, headers={"User-Agent": "hermes-opencode-bootstrap/1.0"}
    )
    with urllib.request.urlopen(req) as resp, dest.open("wb") as out:
        shutil.copyfileobj(resp, out)


def resolve_hermes_home(home: Path) -> Path:
    env_home = os.environ.get("HERMES_HOME")
    if env_home and Path(env_home).is_dir():
        return Path(env_home).resolve()
    appdata_hermes = home / "AppData" / "Local" / "hermes"
    if appdata_hermes.is_dir():
        return appdata_hermes.resolve()
    dot_hermes = home / ".hermes"
    if dot_hermes.is_dir():
        return dot_hermes.resolve()
    appdata_hermes.mkdir(parents=True, exist_ok=True)
    return appdata_hermes.resolve()


def install_python_deps(repo_root: Path) -> None:
    log(
        "Installing Python dependencies (jsonschema, cli-anything-hub, pytest, click)..."
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(repo_root / "requirements.txt"),
        ],
        check=True,
    )


def install_workflow_runner(repo_root: Path, runner_dest: Path) -> None:
    log(f"Installing Gated Workflow Runner -> {runner_dest}")
    if runner_dest.resolve() != (repo_root / "workflow-runner").resolve():
        if runner_dest.exists():
            shutil.rmtree(runner_dest)
        shutil.copytree(repo_root / "workflow-runner", runner_dest)


def install_cli_anything_plugin(
    repo_root: Path, plugin_dest: Path, opencode_config_dir: Path
) -> Path:
    log(f"Installing CLI-Anything plugin & HARNESS.md -> {plugin_dest}")
    if plugin_dest.exists():
        shutil.rmtree(plugin_dest)
    shutil.copytree(repo_root / "cli-anything-plugin", plugin_dest)

    harness_posix = (plugin_dest / "HARNESS.md").resolve().as_posix()
    commands_dest = opencode_config_dir / "commands"
    commands_dest.mkdir(parents=True, exist_ok=True)

    # Remove legacy duplicate singular directory if present
    legacy_cmd = opencode_config_dir / "command"
    if legacy_cmd.is_dir():
        shutil.rmtree(legacy_cmd)

    # Remove accidental HARNESS.md in commands/ if present
    accidental_harness = commands_dest / "HARNESS.md"
    if accidental_harness.is_file():
        accidental_harness.unlink()

    for md_file in (repo_root / "opencode" / "commands").glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        content = content.replace("{{HARNESS_PATH}}", harness_posix)
        (commands_dest / md_file.name).write_text(content, encoding="utf-8")

    log(f"Installed 5 OpenCode slash commands -> {commands_dest}")
    return plugin_dest


def install_skills(
    repo_root: Path,
    hermes_home: Path,
    home: Path,
    runner_dest: Path,
) -> None:
    python_posix = Path(sys.executable).resolve().as_posix()
    runner_posix = runner_dest.resolve().as_posix()

    # 1. gated-project-orchestration -> Hermes skills
    gated_dest = (
        hermes_home / "skills" / "software-development" / "gated-project-orchestration"
    )
    gated_dest.mkdir(parents=True, exist_ok=True)
    gated_text = (
        repo_root / "skills" / "gated-project-orchestration" / "SKILL.md"
    ).read_text(encoding="utf-8")
    gated_text = gated_text.replace("{{RUNNER_DIR}}", runner_posix).replace(
        "{{PYTHON_EXE}}", python_posix
    )
    (gated_dest / "SKILL.md").write_text(gated_text, encoding="utf-8")

    # 2. cli-hub-meta-skill -> Hermes skills
    clihub_dest = hermes_home / "skills" / "software-development" / "cli-hub-meta-skill"
    if clihub_dest.exists():
        shutil.rmtree(clihub_dest)
    shutil.copytree(repo_root / "skills" / "cli-hub-meta-skill", clihub_dest)

    # 3. reverse-engineer-anything -> Shared .agents/skills & Hermes skills
    for target in [
        home / ".agents" / "skills" / "reverse-engineer-anything",
        hermes_home / "skills" / "reverse-engineer-anything",
    ]:
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(repo_root / "skills" / "reverse-engineer-anything", target)

    log(
        "Installed gated-project-orchestration, cli-hub-meta-skill, and reverse-engineer-anything skills."
    )


def install_rea_runtime(tools_dir: Path) -> Path:
    rea_dir = tools_dir / "rea-runtime"
    rea_script = rea_dir / "node_modules" / "rea-agents" / "scripts" / "rea.mjs"
    if rea_script.is_file():
        log(f"REA runtime already present at {rea_dir}")
        return rea_dir
    rea_dir.mkdir(parents=True, exist_ok=True)
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    log(f"Installing {REA_PACKAGE} into {rea_dir}...")
    subprocess.run(
        [
            npm_cmd,
            "install",
            "--prefix",
            str(rea_dir),
            REA_PACKAGE,
            "--no-audit",
            "--no-fund",
        ],
        check=True,
    )
    return rea_dir


def install_native_engines(tools_dir: Path) -> dict[str, str]:
    env_vars: dict[str, str] = {}

    # 1. JDK 21
    jdk_root = tools_dir / "jdk-21"
    java_exe = (
        next(jdk_root.glob("**/bin/java.exe"), None) if jdk_root.exists() else None
    )
    if not java_exe:
        log("Querying Adoptium API for OpenJDK 21 (Windows x64)...")
        req = urllib.request.Request(
            JDK21_API, headers={"User-Agent": "hermes-opencode-bootstrap/1.0"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        jdk_url = data[0]["binary"]["package"]["link"]
        jdk_zip = tools_dir / "openjdk21.zip"
        download_file(jdk_url, jdk_zip)
        with zipfile.ZipFile(jdk_zip, "r") as zf:
            zf.extractall(jdk_root)
        jdk_zip.unlink()
        java_exe = next(jdk_root.glob("**/bin/java.exe"))
    java_home = java_exe.parent.parent.resolve()
    env_vars["JAVA_HOME"] = str(java_home)
    log(f"JDK 21 ready: {java_home}")

    # 2. Ghidra 12.1.4
    ghidra_root = tools_dir / "ghidra"
    ghidra_dir = ghidra_root / "ghidra_12.1.4_PUBLIC"
    if not (ghidra_dir / "Ghidra" / "application.properties").is_file():
        ghidra_zip = tools_dir / "ghidra1214.zip"
        download_file(GHIDRA_URL, ghidra_zip)
        ghidra_root.mkdir(parents=True, exist_ok=True)
        if shutil.which("tar"):
            subprocess.run(
                ["tar", "-xf", str(ghidra_zip), "-C", str(ghidra_root)], check=True
            )
        else:
            with zipfile.ZipFile(ghidra_zip, "r") as zf:
                zf.extractall(ghidra_root)
        ghidra_zip.unlink()
    env_vars["GHIDRA_INSTALL_DIR"] = str(ghidra_dir.resolve())
    log(f"Ghidra 12.1.4 ready: {ghidra_dir}")

    # 3. JADX Headless MCP 0.7.1
    jadx_jar = tools_dir / "jadx" / "jadx-headless-mcp-0.7.1-all.jar"
    if not jadx_jar.is_file() or sha256_file(jadx_jar) != JADX_SHA256:
        download_file(JADX_URL, jadx_jar)
        actual = sha256_file(jadx_jar)
        if actual != JADX_SHA256:
            raise RuntimeError(
                f"JADX SHA-256 mismatch: expected {JADX_SHA256}, got {actual}"
            )
    env_vars["REA_JADX_MCP_JAR"] = str(jadx_jar.resolve())
    log(f"JADX 0.7.1 ready: {jadx_jar}")

    # 4. Apktool 3.0.3
    apktool_dir = tools_dir / "apktool"
    apktool_jar = apktool_dir / "apktool.jar"
    apktool_bat = apktool_dir / "apktool.bat"
    if not apktool_jar.is_file():
        download_file(APKTOOL_URL, apktool_jar)
    apktool_bat.write_text(
        f'@echo off\r\n"{java_exe.resolve()}" -jar "{apktool_jar.resolve()}" %*\r\n',
        encoding="ascii",
    )
    env_vars["REA_APKTOOL_COMMAND"] = str(apktool_bat.resolve())
    log(f"Apktool 3.0.3 ready: {apktool_bat}")

    return env_vars


def configure_clients(
    rea_dir: Path,
    env_vars: dict[str, str],
    opencode_config_dir: Path,
) -> None:
    rea_cmd = (
        rea_dir / "node_modules" / ".bin" / ("rea.cmd" if os.name == "nt" else "rea")
    )
    run_env = os.environ.copy()
    run_env.update(env_vars)
    if "JAVA_HOME" in env_vars:
        run_env["PATH"] = (
            str(Path(env_vars["JAVA_HOME"]) / "bin")
            + os.pathsep
            + run_env.get("PATH", "")
        )

    log("Running REA setup for OpenCode and Hermes...")
    subprocess.run(
        [
            str(rea_cmd),
            "setup",
            "--client",
            "opencode",
            "--client",
            "hermes",
            "--yes",
            "--json",
        ],
        env=run_env,
        check=True,
    )

    # Inject REA_APKTOOL_COMMAND into opencode.json if present
    oc_json = opencode_config_dir / "opencode.json"
    if oc_json.is_file() and "REA_APKTOOL_COMMAND" in env_vars:
        data = json.loads(oc_json.read_text(encoding="utf-8"))
        rea_srv = data.setdefault("mcp", {}).setdefault("servers", {}).get("rea")
        if isinstance(rea_srv, dict):
            rea_srv.setdefault("environment", {})["REA_APKTOOL_COMMAND"] = env_vars[
                "REA_APKTOOL_COMMAND"
            ]
            oc_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def verify_installation(
    runner_dest: Path, rea_dir: Path, env_vars: dict[str, str]
) -> None:
    log("Running 48 Gated Workflow Runner unit & integration tests...")
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-v"],
        cwd=str(runner_dest),
        check=True,
    )

    rea_cmd = (
        rea_dir / "node_modules" / ".bin" / ("rea.cmd" if os.name == "nt" else "rea")
    )
    run_env = os.environ.copy()
    run_env.update(env_vars)
    log("Running REA doctor check...")
    res = subprocess.run(
        [
            str(rea_cmd),
            "doctor",
            "--client",
            "opencode",
            "--client",
            "hermes",
            "--json",
        ],
        env=run_env,
        capture_output=True,
        text=True,
        check=False,
    )
    doc = json.loads(res.stdout)
    log(
        f"REA Doctor healthy={doc.get('healthy')}, availableProviders={doc.get('availableProviders')}"
    )
    if not doc.get("healthy"):
        raise RuntimeError("REA Doctor reported unhealthy status!")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["full", "lite"],
        default="full",
        help="Install mode: 'full' includes JDK 21, Ghidra 12.1.4, JADX 0.7.1, Apktool 3.0.3; 'lite' installs static JS/Web REA + CLI-Anything + Gated Runner.",
    )
    parser.add_argument(
        "--install-root",
        type=Path,
        default=Path.home() / "Jarvis",
        help="Root directory for tools and workflow runner (default: ~/Jarvis)",
    )
    args = parser.parse_args()

    home = Path.home()
    repo_root = Path(__file__).resolve().parent
    install_root = args.install_root.resolve()
    tools_dir = install_root / "tools"
    runner_dest = install_root / "hermes-opencode-workflow"
    plugin_dest = tools_dir / "CLI-Anything" / "cli-anything-plugin"
    opencode_config_dir = home / ".config" / "opencode"
    hermes_home = resolve_hermes_home(home)

    install_python_deps(repo_root)
    install_workflow_runner(repo_root, runner_dest)
    install_cli_anything_plugin(repo_root, plugin_dest, opencode_config_dir)
    install_skills(repo_root, hermes_home, home, runner_dest)
    rea_dir = install_rea_runtime(tools_dir)

    env_vars: dict[str, str] = {}
    if args.mode == "full" and os.name == "nt":
        env_vars = install_native_engines(tools_dir)

    configure_clients(rea_dir, env_vars, opencode_config_dir)
    verify_installation(runner_dest, rea_dir, env_vars)

    log("SUCCESS! All components installed, configured, and verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
