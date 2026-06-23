from typing import Callable
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from snippets import FlatScale
from gi.repository import Gdk

class SliderBox(Box):
    def __init__(
        self,
        left_icon,
        on_left_click: Callable,
        scale_min: float,
        scale_max: float,
        scale_value: float,
        on_scale_change: Callable,
        right_icon=None,
        on_right_click: Callable | None = None,
        **kwargs,
    ):
        self.scale_max = scale_max
        self.scale_min = scale_min
        self.scale = FlatScale(
            h_expand=True,
            h_align="fill",
            style_classes=["scale"],
            min_value=scale_min,
            max_value=scale_max,
            value=scale_value,
        )
        self.scale.connect("value-changed", lambda s: on_scale_change(s))
        self.scale.connect("scroll-event", self.on_scroll)

        super().__init__(
            spacing=12,
            children=[
                Button(
                    style_classes=["applet-misc-button"],
                    child=left_icon,
                    on_clicked=lambda *_: on_left_click(),
                ),

                self.scale,

                Button(
                    style_classes=["applet-misc-button"],
                    child=right_icon,
                    on_clicked=lambda *_: on_right_click() if on_right_click else None,
                ) if right_icon else Button(),
            ],
            **kwargs,
        )

    def on_scroll(self, _, event):
        match event.direction:
            case Gdk.ScrollDirection.UP:
                self.scale.set_value(min(self.scale.value + 1, self.scale_max))
            case Gdk.ScrollDirection.DOWN:
                self.scale.set_value(max(self.scale.value - 1, self.scale_min))
            case Gdk.ScrollDirection.SMOOTH:
                _, dx, dy = event.get_scroll_deltas()
                self.scale.set_value(
                    max(self.scale_min, min(self.scale.value - dy, self.scale_max))
                )
        return True