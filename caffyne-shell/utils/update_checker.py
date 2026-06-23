import subprocess
from pathlib import Path
from gi.repository import GLib
from loguru import logger

REPO_PATH = Path(__file__).parent.parent

_check_claimed = False


def claim_update_check() -> bool:
    global _check_claimed
    if _check_claimed:
        return False
    _check_claimed = True
    return True


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=REPO_PATH,
        timeout=10,
    )


def check_for_updates(on_update_available) -> None:
    def _worker():
        try:
            _run(["git", "fetch"])
            result = _run(["git", "rev-list", "HEAD..@{u}", "--count"])
            behind = int(result.stdout.strip())
        except subprocess.TimeoutExpired:
            logger.warning("[UpdateChecker] git fetch timed out")
            return
        except Exception as e:
            logger.warning(f"[UpdateChecker] failed to check for updates: {e}")
            return

        if behind > 0:
            GLib.idle_add(on_update_available, behind)

    GLib.Thread.new(None, _worker)


def do_pull(on_success, on_failure) -> None:
    def _worker():
        try:
            result = _run(["git", "pull"])
            if result.returncode == 0:
                GLib.idle_add(on_success)
            else:
                GLib.idle_add(on_failure, result.stderr.strip() or "git pull returned an error")
        except subprocess.TimeoutExpired:
            GLib.idle_add(on_failure, "git pull timed out")
        except Exception as e:
            GLib.idle_add(on_failure, str(e))

    GLib.Thread.new(None, _worker)


def restart_shell() -> None:
    import os, sys
    os.execv(sys.executable, [sys.executable] + sys.argv)