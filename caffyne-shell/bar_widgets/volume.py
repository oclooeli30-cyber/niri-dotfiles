from .base import StatButton
from services.singletons import audio
from icons import VolumeIcon
 
class VolumeButton(StatButton):
    def __init__(self, monitor_id, vertical, variant=None, **kwargs):
        super().__init__(
            icon=VolumeIcon,
            label="",
            variant=variant or "icon+label",
            **kwargs,
        )
        audio.connect("speaker-changed", self._on_speaker_changed)
        if audio.speaker:
            self._on_speaker_changed()
 
    def _on_speaker_changed(self, *_):
        if not audio.speaker:
            return
        if getattr(self, "_bound_speaker", None) is audio.speaker:
            return

        self._bound_speaker = audio.speaker
        vol = int(audio.speaker.volume)
        self._update_label(f"{vol}%")
        self._update_value(vol)
 
        audio.speaker.connect("notify::volume", lambda obj, _: (
            self._update_label(f"{int(obj.volume)}%"),
            self._update_value(int(obj.volume)),
        ))

    def _adjust(self, direction: int):
        if audio.speaker:
            audio.speaker.volume -= direction  