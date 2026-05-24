import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEPLOY_TEMPLATE = ROOT / "deploy" / "Windows" / "template.yaml"
DEPLOY_CONFIG = ROOT / "config" / "deploy.yaml"
PERSIST_ROOT = Path(os.environ.get("SRC_DATA_DIR", "/data/starrailcopilot"))
PERSISTENT_DIRS = ("config", "log", "screenshots")


def _yaml_scalar(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def ensure_deploy_config() -> None:
    port = int(os.environ.get("PORT", "7860"))
    password = os.environ.get("SRC_WEBUI_PASSWORD") or os.environ.get("SPACE_PASSWORD")

    overrides = {
        "Repository": "global",
        "GitExecutable": "git",
        "AutoUpdate": False,
        "KeepLocalChanges": True,
        "PythonExecutable": sys.executable,
        "InstallDependencies": False,
        "AdbExecutable": "adb",
        "ReplaceAdb": False,
        "AutoConnect": False,
        "InstallUiautomator2": False,
        "StartOcrServer": False,
        "EnableReload": False,
        "CheckUpdateInterval": 0,
        "AutoRestartTime": None,
        "EnableRemoteAccess": False,
        "WebuiHost": "0.0.0.0",
        "WebuiPort": port,
        "Password": password,
        "CDN": False,
        "Run": None,
        "WebuiSSLKey": None,
        "WebuiSSLCert": None,
        "AppAsarUpdate": False,
        "NoSandbox": True,
    }

    text = DEPLOY_TEMPLATE.read_text(encoding="utf-8").replace("\\", "/")
    for key, value in overrides.items():
        text = re.sub(
            rf"(^\s*{re.escape(key)}:\s*).*$",
            lambda match, scalar=_yaml_scalar(value): f"{match.group(1)}{scalar}",
            text,
            flags=re.MULTILINE,
        )

    DEPLOY_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    DEPLOY_CONFIG.write_text(text, encoding="utf-8")


def _copy_missing(source: Path, target: Path) -> None:
    if not source.exists():
        return

    if source.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        for child in source.iterdir():
            _copy_missing(child, target / child.name)
    elif not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _replace_with_symlink(source: Path, target: Path) -> None:
    if source.is_symlink():
        if source.resolve() == target.resolve():
            return
        source.unlink()
    elif source.exists():
        if source.is_dir():
            shutil.rmtree(source)
        else:
            source.unlink()

    source.symlink_to(target, target_is_directory=True)


def prepare_persistent_paths() -> None:
    data_root = PERSIST_ROOT.parent
    if not data_root.exists():
        print(f"[hf-space] Persistent storage mount not found at {data_root}; using image-local runtime data")
        return

    try:
        test_file = data_root / ".src-write-test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
    except OSError as exc:
        print(f"[hf-space] Persistent storage unavailable at {data_root}: {exc}")
        return

    print(f"[hf-space] Using persistent runtime data at {PERSIST_ROOT}")
    for dirname in PERSISTENT_DIRS:
        app_path = ROOT / dirname
        data_path = PERSIST_ROOT / dirname
        data_path.mkdir(parents=True, exist_ok=True)

        if app_path.exists() and not app_path.is_symlink():
            _copy_missing(app_path, data_path)

        _replace_with_symlink(app_path, data_path)


def main() -> int:
    prepare_persistent_paths()
    ensure_deploy_config()
    port = os.environ.get("PORT", "7860")
    cmd = [
        sys.executable,
        "gui.py",
        "--host",
        "0.0.0.0",
        "--port",
        port,
    ]
    if os.environ.get("SRC_WEBUI_PASSWORD") or os.environ.get("SPACE_PASSWORD"):
        cmd.extend(["--key", os.environ.get("SRC_WEBUI_PASSWORD") or os.environ["SPACE_PASSWORD"]])
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
