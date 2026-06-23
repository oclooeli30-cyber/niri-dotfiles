import math
import cairo
from typing import Literal, Callable
from gi.repository import Gtk
from fabric.widgets.box import Box
from snippets.animator import Animator

class AppletReveal(Box):
    """
    Cairo-drawn widget that animates an applet popup in with a scale + fade,
    anchored to the bar edge (top or bottom center).

    Scales from SCALE_START → 1.0 and fades from 0.0 → 1.0 simultaneously,
    growing outward from the bar edge so it feels physically connected to it.

    Usage:
        reveal = AppletReveal(
            direction="down",   # "down" for top bar, "up" for bottom bar
            child=your_content,
        )
        reveal.open()
        reveal.close(on_done=cb)

    Optional progress callback (for blur region tracking etc):
        reveal.progress_cb = lambda p: update_blur(p)
    """

    SCALE_START = 0.40

    def __init__(
        self,
        direction: Literal["down", "up"] = "down",
        child: Gtk.Widget | None = None,
        open_bezier: tuple[float, float, float, float] = (0.22, 1.0, 0.36, 1.0),
        close_bezier: tuple[float, float, float, float] = (0.5, 0.0, 0.75, 0.0),
        open_duration: float = 0.28,
        close_duration: float = 0.18,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._direction = direction
        self._progress = 0.0
        self._target = 0.0
        self._on_close_callbacks: list = []
        self.progress_cb: Callable[[float], None] | None = None

        if child:
            self.add(child)

        self.set_app_paintable(True)

        self.open_animator = (
            Animator(
                bezier_curve=open_bezier,
                duration=open_duration,
                min_value=0.0,
                max_value=1.0,
                tick_widget=self,
            )
            .build()
            .unwrap()
        )

        self.close_animator = (
            Animator(
                bezier_curve=close_bezier,
                duration=close_duration,
                min_value=0.0,
                max_value=1.0,
                tick_widget=self,
            )
            .build()
            .unwrap()
        )

        self.open_animator.connect(
            "notify::value", lambda a, _: self._set_progress(a.value)
        )
        self.close_animator.connect(
            "notify::value", lambda a, _: self._set_progress(1.0 - a.value)
        )
        self.close_animator.connect("finished", self._on_close_finished)

    def open(self):
        """Animate the applet in. Safe to call mid-close."""
        self._target = 1.0
        self.close_animator.pause()

        self.open_animator.pause()
        self.open_animator.min_value = self._progress
        self.open_animator.max_value = 1.0
        self.open_animator.value = self._progress
        self.open_animator._start_time = None
        self.open_animator.play()

    def close(self, on_done=None):
        """Animate the applet out. on_done called when animation finishes."""
        self._target = 0.0

        if on_done:
            def _once(*_):
                on_done()
                try:
                    self._on_close_callbacks.remove(_once)
                except ValueError:
                    pass
            self._on_close_callbacks.append(_once)

        self.open_animator.pause()

        start = 1.0 - self._progress
        self.close_animator.pause()
        self.close_animator.min_value = start
        self.close_animator.max_value = 1.0
        self.close_animator.value = start
        self.close_animator._start_time = None
        self.close_animator.play()

    @property
    def direction(self) -> str:
        return self._direction

    @direction.setter
    def direction(self, value: Literal["down", "up"]):
        self._direction = value
        self.queue_draw()

    @property
    def progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float):
        self._progress = max(0.0, min(value, 1.0))
        self.set_opacity(self._progress)
        if self.progress_cb:
            self.progress_cb(self._progress)
        self.queue_draw()

    def _on_close_finished(self, *_):
        if self._target == 0.0:
            for cb in self._on_close_callbacks:
                cb()

    def do_draw(self, cr: cairo.Context) -> bool:
        p = self._progress
        if p <= 0.0:
            return True

        w = self.get_allocated_width()
        h = self.get_allocated_height()

        scale = self.SCALE_START + (1.0 - self.SCALE_START) * _ease_out_expo(p)

        anchor_x = w / 2.0
        anchor_y = 0.0 if self._direction == "down" else h

        radius = int(
            self.get_style_context().get_property(
                "border-radius", self.get_state_flags()
            )
        )
        radius = max(radius, 0)

        cr.save()

        cr.translate(anchor_x, anchor_y)
        cr.scale(scale, scale)
        cr.translate(-anchor_x, -anchor_y)

        _draw_rounded_rect(cr, 0, 0, w, h, radius)
        cr.clip()

        Gtk.Box.do_draw(self, cr)

        cr.restore()
        return True

def _ease_out_expo(t: float) -> float:
    if t >= 1.0:
        return 1.0
    return 1.0 - pow(2.0, -10.0 * t)


def _draw_rounded_rect(
    cr: cairo.Context,
    x: float, y: float,
    w: float, h: float,
    r: float,
):
    r = min(r, w / 2, h / 2)
    cr.move_to(x + r, y)
    cr.line_to(x + w - r, y)
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.line_to(x + w, y + h - r)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.line_to(x + r, y + h)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.line_to(x, y + r)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()