import os
from fabric.utils import exec_shell_command_async, DesktopApp
import re

def clean_cmd(cmd: str) -> str:
    return re.sub(r'%\w', '', cmd).strip()

def dispatch_app(app: DesktopApp) -> bool:
    cmd = clean_cmd(app.command_line)
    if os.getenv("NIRI_SOCKET"):
        exec_shell_command_async(f"niri msg action spawn -- {cmd}")
    elif os.getenv("HYPRLAND_INSTANCE_SIGNATURE"):
        exec_shell_command_async(
            f'hyprctl dispatch \'hl.dsp.exec_cmd("{cmd}")\''
        )
    elif os.getenv("MANGO_INSTANCE_SIGNATURE"):
        exec_shell_command_async(f"mmsg dispatch spawn, {cmd}")
    else:
        return False
    return True