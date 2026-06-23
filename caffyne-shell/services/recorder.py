import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from fabric.core.service import Property, Service
from loguru import logger

import subprocess

def find_sink_monitor() -> Optional[str]:
    """Return the monitor source of the default PulseAudio/PipeWire sink."""
    try:

        sink = subprocess.check_output(
            ["pactl", "get-default-sink"], text=True
        ).strip()

        monitor = f"{sink}.monitor"
        
        sources = subprocess.check_output(
            ["pactl", "list", "short", "sources"], text=True
        )
        if monitor in sources:
            return monitor
        
        logger.warning(f"[RecorderService] Expected monitor '{monitor}' not found in sources")
    except FileNotFoundError:
        logger.error("[RecorderService] pactl not found — is PipeWire/PulseAudio running?")
    except Exception as e:
        logger.error(f"[RecorderService] Failed to query audio devices: {e}")
    return None

class RecorderService(Service):

    @Property(bool, "readable", default_value=False)
    def active(self) -> bool:
        return self._active

    @Property(str, "readable", default_value="")
    def last_recording(self) -> str:
        return self._last_recording

    def __init__(
        self,
        output_dir: str = "~/Videos/Recordings",
        container: str = "mp4",
        codec: str = "libx264",
        framerate: int = 60,
        audio: bool = True,
        **kwargs,
    ):
        """
        output_dir:  Where recordings are saved (~ is expanded).
        container:   Output container format, e.g. "mp4", "mkv".
        codec:       Video codec passed to wf-recorder's -c flag.
        framerate:   Recording framerate.
        audio:       Whether to record audio via wf-recorder's -a flag.
        """
        self._output_dir = Path(output_dir).expanduser()
        self._container = container
        self._codec = codec
        self._framerate = framerate
        self._audio = audio
        self._process: Optional[subprocess.Popen] = None
        self._active = False
        self._last_recording = ""
        self._current_file: Optional[Path] = None

        super().__init__(**kwargs)

        self._output_dir.mkdir(parents=True, exist_ok=True)

    def start(self, output: Optional[str] = None):
        if self._active:
            logger.warning("[RecorderService] Already recording, ignoring start()")
            return

        self._current_file = self._output_dir / (
            f"recording_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.{self._container}"
        )

        if self._audio:
            audio_device = find_sink_monitor()
            if audio_device is None:
                logger.warning("[RecorderService] No sink monitor found, recording without audio")
                self._audio_device = None
            else:
                logger.info(f"[RecorderService] Using audio device: {audio_device}")
                self._audio_device = audio_device
        else:
            self._audio_device = None

        args = self._build_args(output)
        logger.debug(f"[RecorderService] Args: {' '.join(args)}")

        try:
            self._process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._active = True
            self.notify("active")
            logger.info(f"[RecorderService] Started (pid {self._process.pid}) → {self._current_file}")
        except FileNotFoundError:
            logger.error("[RecorderService] wf-recorder not found — is it installed?")
        except Exception as e:
            logger.error(f"[RecorderService] Failed to start: {e}")

    def stop(self):
        """Stop recording and finalise the output file."""
        if not self._active:
            logger.warning("[RecorderService] Not recording, ignoring stop()")
            return

        logger.info("[RecorderService] Stopping...")
        self._kill()
        self._active = False
        self.notify("active")

        if self._current_file and self._current_file.exists():
            self._last_recording = str(self._current_file)
            self.notify("last-recording")
            logger.info(f"[RecorderService] Saved → {self._last_recording}")
        else:
            logger.warning("[RecorderService] Output file not found after stop")

        self._current_file = None

    def toggle(self, output: Optional[str] = None):
        """Toggle recording on/off."""
        if self._active:
            self.stop()
        else:
            self.start(output)

    def _build_args(self, output: Optional[str]) -> list[str]:
        args = [
            "wf-recorder",
            "-f", str(self._current_file),
            "-c", self._codec,
            "-r", str(self._framerate),
        ]

        if output:
            args += ["-o", output]

        if self._audio and self._audio_device:
            args += [f"-a={self._audio_device}"]

        return args

    def _kill(self):
        if self._process is None:
            return
        try:

            self._process.terminate()
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("[RecorderService] SIGTERM timed out, sending SIGKILL")
            self._process.kill()
            self._process.wait()
        except Exception as e:
            logger.warning(f"[RecorderService] Error stopping process: {e}")
        finally:
            self._process = None