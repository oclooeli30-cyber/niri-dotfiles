from .slider import SliderBox
from icons import VolumeIcon
from snippets import Icon
from services.singletons import audio

class VolumeSlider(SliderBox):
    def __init__(self, stack, **kwargs):
        super().__init__(
            left_icon=VolumeIcon(stream=audio.speaker, size=16),
            on_left_click=lambda *_: audio.speaker.set_muted(not audio.speaker.muted),
            scale_min=0,
            scale_max=100,
            scale_value=audio.speaker.volume if audio.speaker else 0,
            on_scale_change=lambda s: audio.speaker.set_volume(s.get_value()) if audio.speaker and not self._updating else None,
            on_right_click=lambda *_: stack.set_visible_child_name("audio"),
            right_icon=Icon(icon_name="chevron-right", icon_size=16),
            **kwargs,
        )
        self._dragging = False
        self._updating = False
        self.scale.connect("button-press-event", lambda *_: setattr(self, "_dragging", True))
        self.scale.connect("button-release-event", lambda *_: setattr(self, "_dragging", False))

        if audio.speaker:
            audio.speaker.connect("notify::volume", self._on_volume_changed)

        audio.connect(
            "speaker-changed",
            lambda *_: self._on_speaker_changed(),
        )

    def _on_volume_changed(self, obj, _):
        if self._dragging:
            return
        self._updating = True
        self.scale.set_value(obj.volume)
        self._updating = False

    def _on_speaker_changed(self):
        if not audio.speaker:
            return
        if getattr(self, "_bound_speaker", None) is audio.speaker:
            return

        self._bound_speaker = audio.speaker
        audio.speaker.connect("notify::volume", self._on_volume_changed)

        self._updating = True
        self.scale.set_value(audio.speaker.volume)
        self._updating = False