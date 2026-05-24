import hashlib
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEPLOY_TEMPLATE = ROOT / "deploy" / "Windows" / "template.yaml"
DEPLOY_CONFIG = ROOT / "config" / "deploy.yaml"
PERSIST_ROOT = Path(os.environ.get("SRC_DATA_DIR", "/data/starrailcopilot"))
PERSISTENT_DIRS = ("config", "log", "screenshots")
PG_TABLE = "src_space_files"
PG_DEFAULT_EXCLUDES = ("config/deploy.yaml", "config/reloadalas", "config/reloadflag")


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


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.environ.get(name)
    if not value:
        return default
    return tuple(item.strip().replace("\\", "/").strip("/") for item in value.split(",") if item.strip())


def _pg_dsn() -> str | None:
    return os.environ.get("SRC_DATABASE_URL") or os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


def _pg_namespace() -> str:
    return os.environ.get("SRC_PG_NAMESPACE") or os.environ.get("SPACE_ID") or "starrailcopilot"


def _pg_sync_dirs() -> tuple[str, ...]:
    return _csv_env("SRC_PG_SYNC_DIRS", ("config",))


def _pg_excludes() -> tuple[str, ...]:
    return _csv_env("SRC_PG_EXCLUDES", PG_DEFAULT_EXCLUDES)


def _is_pg_path_allowed(path: str, sync_dirs: tuple[str, ...], excludes: tuple[str, ...]) -> bool:
    rel = Path(path)
    if rel.is_absolute() or ".." in rel.parts:
        return False
    normalized = rel.as_posix().strip("/")
    if normalized in excludes:
        return False
    return any(normalized == dirname or normalized.startswith(f"{dirname}/") for dirname in sync_dirs)


class PostgresFileSync:
    def __init__(self) -> None:
        self.dsn = _pg_dsn()
        self.namespace = _pg_namespace()
        self.sync_dirs = _pg_sync_dirs()
        self.excludes = _pg_excludes()
        self.interval = int(os.environ.get("SRC_PG_SYNC_INTERVAL", "60"))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.dsn)

    def _connect(self):
        import psycopg

        return psycopg.connect(self.dsn, autocommit=True)

    def _ensure_table(self, conn) -> None:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {PG_TABLE} (
                namespace TEXT NOT NULL,
                path TEXT NOT NULL,
                content BYTEA NOT NULL,
                sha256 TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (namespace, path)
            )
            """
        )

    def restore(self) -> None:
        if not self.enabled:
            print("[hf-space] PostgreSQL config sync disabled; set SRC_DATABASE_URL to enable it")
            return

        try:
            with self._connect() as conn:
                self._ensure_table(conn)
                rows = conn.execute(
                    f"SELECT path, content FROM {PG_TABLE} WHERE namespace = %s",
                    (self.namespace,),
                ).fetchall()
        except Exception as exc:
            print(f"[hf-space] PostgreSQL restore skipped: {exc}")
            return

        restored = 0
        for path, content in rows:
            if not _is_pg_path_allowed(path, self.sync_dirs, self.excludes):
                continue
            target = ROOT / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bytes(content))
            restored += 1
        print(f"[hf-space] Restored {restored} file(s) from PostgreSQL namespace '{self.namespace}'")

    def _iter_local_files(self) -> dict[str, tuple[str, bytes]]:
        files: dict[str, tuple[str, bytes]] = {}
        for dirname in self.sync_dirs:
            directory = ROOT / dirname
            if not directory.exists():
                continue
            for file in directory.rglob("*"):
                if not file.is_file():
                    continue
                rel = file.relative_to(ROOT).as_posix()
                if not _is_pg_path_allowed(rel, self.sync_dirs, self.excludes):
                    continue
                content = file.read_bytes()
                files[rel] = (hashlib.sha256(content).hexdigest(), content)
        return files

    def upload_once(self) -> None:
        if not self.enabled:
            return

        try:
            local_files = self._iter_local_files()
            with self._connect() as conn:
                self._ensure_table(conn)
                rows = conn.execute(
                    f"SELECT path, sha256 FROM {PG_TABLE} WHERE namespace = %s",
                    (self.namespace,),
                ).fetchall()
                remote = {path: sha256 for path, sha256 in rows}

                uploaded = 0
                for path, (sha256, content) in local_files.items():
                    if remote.get(path) == sha256:
                        continue
                    conn.execute(
                        f"""
                        INSERT INTO {PG_TABLE} (namespace, path, content, sha256, updated_at)
                        VALUES (%s, %s, %s, %s, now())
                        ON CONFLICT (namespace, path)
                        DO UPDATE SET content = EXCLUDED.content,
                                      sha256 = EXCLUDED.sha256,
                                      updated_at = now()
                        """,
                        (self.namespace, path, content, sha256),
                    )
                    uploaded += 1

                deleted = 0
                local_paths = set(local_files)
                for path in remote:
                    if path in local_paths or not _is_pg_path_allowed(path, self.sync_dirs, self.excludes):
                        continue
                    conn.execute(
                        f"DELETE FROM {PG_TABLE} WHERE namespace = %s AND path = %s",
                        (self.namespace, path),
                    )
                    deleted += 1
        except Exception as exc:
            print(f"[hf-space] PostgreSQL upload skipped: {exc}")
            return

        if uploaded or deleted:
            print(f"[hf-space] PostgreSQL sync uploaded {uploaded}, deleted {deleted}")

    def start(self) -> None:
        if not self.enabled or self.interval <= 0:
            return

        def worker() -> None:
            while not self._stop.wait(self.interval):
                self.upload_once()

        self._thread = threading.Thread(target=worker, name="postgres-file-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self.enabled:
            return
        self._stop.set()
        self.upload_once()


def main() -> int:
    prepare_persistent_paths()
    pg_sync = PostgresFileSync()
    pg_sync.restore()
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
    process = subprocess.Popen(cmd, cwd=ROOT)

    def handle_signal(signum, _frame) -> None:
        print(f"[hf-space] Received signal {signum}; syncing PostgreSQL state before shutdown")
        pg_sync.stop()
        process.terminate()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    pg_sync.upload_once()
    pg_sync.start()
    try:
        return process.wait()
    finally:
        pg_sync.stop()


if __name__ == "__main__":
    raise SystemExit(main())
