import os
import subprocess
from typing import Optional
from fabric.core.service import Service, Property
from gi.repository import GLib
from loguru import logger

STASIS_CONFIG = os.path.expanduser("~/.config/stasis/stasis.rune")


def _get_screen_commands() -> tuple[str, str]:
    if os.getenv("NIRI_SOCKET"):
        return (
            "niri msg action power-off-monitors",
            "niri msg action power-on-monitors",
        )
    elif os.getenv("HYPRLAND_INSTANCE_SIGNATURE"):
        return (
            "hyprctl dispatch dpms off",
            "hyprctl dispatch dpms on",
        )
    elif os.getenv("MANGO_INSTANCE_SIGNATURE"):
        return (
            "mango msg dpms off",
            "mango msg dpms on",
        )
    else:
        return (
            "wlopm --off '*'",
            "wlopm --on '*'",
        )


class StasisIdleService(Service):

    @Property(bool, "readable", default_value=False)
    def active(self) -> bool:
        return self._active

    @Property(bool, "readable", default_value=False)
    def on_battery(self) -> bool:
        return self._on_battery

    def __init__(self, rules: list[dict], **kwargs):
        self._rules: list[dict] = list(rules)
        self._active = False
        self._on_battery = False
        self._upower = None

        super().__init__(**kwargs)

        self._setup_upower()

    def start(self):
        if self._active:
            return
        logger.info("[StasisIdleService] Starting...")
        self._active = True
        self.notify("active")
        self._write_config()
        self._reload()

    def stop(self):
        if not self._active:
            return
        logger.info("[StasisIdleService] Stopping...")
        self._active = False
        self.notify("active")

    def update_rules(self, rules: list[dict]):
        logger.info("[StasisIdleService] Rules updated, reloading...")
        self._rules = list(rules)
        if self._active:
            self._write_config()
            self._reload()

    def _setup_upower(self):
        try:
            from services.singletons import battery
            self._upower = battery
            self._on_battery = self._check_battery()
            self._upower.connect("changed", self._on_power_changed)
            logger.info("[StasisIdleService] Battery service connected")
        except Exception as e:
            logger.warning(f"[StasisIdleService] Battery service unavailable: {e}")

    def _check_battery(self) -> bool:
        if not self._upower:
            return False
        try:
            return self._upower.discharging
        except Exception:
            return False

    def _on_power_changed(self, *_):
        now_battery = self._check_battery()
        if now_battery == self._on_battery:
            return
        self._on_battery = now_battery
        self.notify("on-battery")
        state = "battery" if now_battery else "AC"
        logger.info(f"[StasisIdleService] Power state → {state}, reloading...")
        if self._active:
            GLib.timeout_add(1000, self._reload_once)

    def _reload_once(self):
        self._write_config()
        self._reload()
        return False

    def _get_timeout(self, name: str) -> int:
        for rule in self._rules:
            if rule.get("name") == name and rule.get("enabled", True):
                mins = rule["timeout_bat"] if self._on_battery else rule["timeout_ac"]
                return int(mins * 60)
        return 0

    def _write_config(self) -> None:
        screen_off, screen_on = _get_screen_commands()
        lock_cmd = "python3 /home/eli/.config/caffyne-shell/lockscreen.py &"
        suspend_cmd = "loginctl suspend"

        off_t = self._get_timeout("screen-off") or 600
        lock_t = self._get_timeout("lock") or 900
        susp_t = self._get_timeout("suspend") or 900

        content = f"""@author "Eli"
@description "Caffyne shell idle management (auto-generated)"

default:
  enable_loginctl true
  enable_dbus_inhibit true
  monitor_media true
  ignore_remote_media true
  debounce_seconds 5

  inhibit_apps [
    "mpv"
    "vlc"
    r"steam_app_.*"
  ]

  screen_off:
    timeout {off_t}
    command "{screen_off}"
    resume_command "{screen_on}"
  end

  lock_screen:
    timeout {lock_t}
    command "{lock_cmd}"
  end

  suspend:
    timeout {susp_t}
    command "{suspend_cmd}"
  end

  ac:
    screen_off:
      timeout {off_t}
      command "{screen_off}"
      resume_command "{screen_on}"
    end

    lock_screen:
      timeout {lock_t}
      command "{lock_cmd}"
    end

    suspend:
      timeout {susp_t}
      command "{suspend_cmd}"
    end
  end

  battery:
    screen_off:
      timeout {self._get_timeout("screen-off") or 120}
      command "{screen_off}"
      resume_command "{screen_on}"
    end

    lock_screen:
      timeout {self._get_timeout("lock") or 300}
      command "{lock_cmd}"
    end

    suspend:
      timeout {self._get_timeout("suspend") or 600}
      command "{suspend_cmd}"
    end
  end
end
"""
        try:
            os.makedirs(os.path.dirname(STASIS_CONFIG), exist_ok=True)
            with open(STASIS_CONFIG, "w") as f:
                f.write(content)
            logger.info("[StasisIdleService] wrote stasis.rune")
        except Exception as e:
            logger.error(f"[StasisIdleService] failed to write config: {e}")

    def _reload(self):
        try:
            subprocess.run(
                ["stasis", "reload"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            logger.info("[StasisIdleService] stasis reloaded")
        except FileNotFoundError:
            logger.error("[StasisIdleService] stasis not found")
        except subprocess.TimeoutExpired:
            logger.warning("[StasisIdleService] stasis reload timed out")
        except Exception as e:
            logger.error(f"[StasisIdleService] stasis reload failed: {e}")