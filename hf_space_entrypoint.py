import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEPLOY_TEMPLATE = ROOT / "deploy" / "Windows" / "template.yaml"
DEPLOY_CONFIG = ROOT / "config" / "deploy.yaml"


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


def main() -> int:
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
