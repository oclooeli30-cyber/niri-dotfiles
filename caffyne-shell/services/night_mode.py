import subprocess
from typing import Optional
from fabric.core.service import Service, Property
from loguru import logger

class NightModeService(Service):

    @Property(bool, "read-write", default_value=False)
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        if value == self._enabled:
            return
        self._enabled = value
        self.notify("enabled")
        if value:
            self._spawn()
        else:
            self._kill()

    def __init__(self, night_temp: int = 3500, day_temp: int = 6500, **kwargs):
        self._night_temp = night_temp
        self._day_temp = day_temp
        self._process: Optional[subprocess.Popen] = None
        self._enabled = False
        super().__init__(**kwargs)

    def toggle(self):
        self.enabled = not self._enabled

    def _spawn(self):
        self._process = subprocess.Popen(
            ["wlsunset", "-t", str(self._night_temp), "-T", str(self._day_temp), "-s", "00:00", "-S", "00:01"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f"[NightModeService] Started (pid {self._process.pid})")

    def _kill(self):
        if self._process is None:
            return
        try:
            self._process.terminate()
            self._process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        except Exception as e:
            logger.warning(f"[NightModeService] Error killing process: {e}")
        finally:
            self._process = None