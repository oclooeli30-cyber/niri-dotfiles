from .slider import SliderBox
from icons import MicrophoneIcon
from snippets import Icon
from services.singletons import audio

class MicrophoneSlider(SliderBox):
    def __init__(self, stack, **kwargs):
        super().__init__(
            left_icon=MicrophoneIcon(stream=audio.microphone, size=16),
            on_left_click=lambda *_: audio.microphone.set_muted(not audio.microphone.muted),
            scale_min=0,
            scale_max=100,
            scale_value=audio.microphone.volume if audio.microphone else 0,
            on_scale_change=lambda s: audio.microphone.set_volume(s.get_value()) if audio.microphone and not self._updating else None,
            on_right_click=lambda *_: stack.set_visible_child_name("audio"),
            right_icon=Icon(icon_name="chevron-right", icon_size=16),
            **kwargs,
        )
        self._dragging = False
        self._updating = False
        self.scale.connect("button-press-event", lambda *_: setattr(self, "_dragging", True))
        self.scale.connect("button-release-event", lambda *_: setattr(self, "_dragging", False))

        if audio.microphone:
            audio.microphone.connect("notify::volume", self._on_volume_changed)

        audio.connect(
            "microphone-changed",
            lambda *_: self._on_microphone_changed(),
        )

    def _on_volume_changed(self, obj, _):
        if self._dragging:
            return
        self._updating = True
        self.scale.set_value(obj.volume)
        self._updating = False

    def _on_microphone_changed(self):
        if not audio.microphone:
            return
        if getattr(self, "_bound_microphone", None) is audio.microphone:
            return

        self._bound_microphone = audio.microphone
        audio.microphone.connect("notify::volume", self._on_volume_changed)

        self._updating = True
        self.scale.set_value(audio.microphone.volume)
        self._updating = False