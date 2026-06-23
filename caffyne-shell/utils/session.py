import subprocess

def get_session_manager() -> str:
    """Returns 'loginctl' if elogind is running, otherwise 'systemctl'."""
    try:
        result = subprocess.run(
            ["ps", "-eo", "comm="],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            if line.strip() in ("elogind", "elogind-daemon"):
                return "loginctl"
    except Exception:
        pass
    return "systemctl"

SESSION_MANAGER = get_session_manager()