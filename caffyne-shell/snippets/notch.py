import math
import cairo
from typing import Literal
from gi.repository import Gtk
from fabric.widgets.box import Box
from snippets.animator import Animator

class NotchReveal(Box):
    """
    A Cairo-drawn widget that animates a rounded rect expanding from the bar edge.
    Drop this as the outermost child of your AppletWindow (or any popup).

    Usage:
        reveal = NotchReveal(
            direction="down",           # "down" for top bar, "up" for bottom bar
            bezier_curve=(0.34, 1.4, 0.64, 1.0),
            duration=0.45,
            child=your_content,
        )
        reveal.open()   # animate in
        reveal.close()  # animate out
    """

    def __init__(
        self,
        direction: Literal["down", "up"] = "down",
        bezier_curve: tuple[float, float, float, float] = (0.34, 1.4, 0.64, 1.0),
        close_bezier_curve: tuple[float, float, float, float] = (0.4, 0.0, 0.2, 1.0),
        duration: float = 0.45,
        child: Gtk.Widget | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._direction = direction
        self._progress = 0.0
        self._target = 0.0

        if child:
            self.add(child)

        self.set_app_paintable(True)

        self.open_animator = (
            Animator(
                bezier_curve=bezier_curve,
                duration=duration,
                min_value=0.0,
                max_value=1.0,
                tick_widget=self,
            )
            .build()
            .unwrap()
        )

        self.close_animator = (
            Animator(
                bezier_curve=close_bezier_curve,
                duration=duration * 0.8,
                min_value=0.0,
                max_value=1.0,
                tick_widget=self,
            )
            .build()
            .unwrap()
        )

        self.open_animator.connect("notify::value", lambda a, _: self._set_progress(a.value))
        self.close_animator.connect("notify::value", lambda a, _: self._set_progress(1.0 - a.value))
        self.close_animator.connect("finished", self._on_finished)

        self._on_open_callbacks: list = []
        self._on_close_callbacks: list = []
    def do_get_preferred_height(self):
        children = self.get_children()
        if not children:
            return 0, 0
        minimum, natural = children[0].get_preferred_height()
        overshoot_px = int(natural * 0.15)
        return minimum, natural + overshoot_px

    def do_get_preferred_width(self):
        children = self.get_children()
        if not children:
            return 0, 0
        minimum, natural = children[0].get_preferred_width()
        overshoot_px = int(natural * 0.08)
        return minimum, natural + overshoot_px
    def _set_progress(self, value: float):
        self._progress = value
        self.queue_draw()

    def _on_finished(self, *_):
        if self._target == 0.0:
            for cb in self._on_close_callbacks:
                cb()

    def open(self):
        """Animate the popup open."""
        self._target = 1.0
        self.close_animator.pause()

        self.open_animator.pause()
        self.open_animator.min_value = self._progress
        self.open_animator.max_value = 1.0
        self.open_animator.value = self._progress
        self.open_animator._start_time = None
        self.open_animator.play()

    def close(self, on_done=None):
        """Animate the popup closed. Optionally call on_done when finished."""
        self._target = 0.0
        if on_done:
            def _once(*_):
                on_done()
                self._on_close_callbacks.remove(_once)
            self._on_close_callbacks.append(_once)

        self.open_animator.pause()

        start = 1.0 - self._progress
        self.close_animator.pause()
        self.close_animator.min_value = start
        self.close_animator.max_value = 1.0
        self.close_animator.value = start
        self.close_animator._start_time = None
        self.close_animator.play()

    def toggle(self):
        if self._target == 1.0:
            self.close()
        else:
            self.open()

    @property
    def progress(self) -> float:
        return self._progress

    @property
    def direction(self) -> str:
        return self._direction

    @direction.setter
    def direction(self, value: Literal["down", "up"]):
        self._direction = value
        self.queue_draw()

    def do_draw(self, cr: cairo.Context) -> bool:
        p = self._progress
        if p <= 0.0:
            return True
        print(f"[notch] progress={p:.3f} target={self._target} cur_h={self.get_allocated_height() * p:.1f}")

        w = self.get_allocated_width()
        h = self.get_allocated_height()

        radius = int(
            self.get_style_context().get_property(
                "border-radius", self.get_state_flags()
            )
        )
        radius = max(radius, 0)

        p_clamped = min(p, 1.0)
        p_w = _ease_out_expo(p_clamped)
        p_h = p

        cur_w = w * p_w
        cur_h = h * p_h
        cur_r = min(radius, cur_w / 2, cur_h / 2) if (cur_w > 0 and cur_h > 0) else 0

        x = (w - cur_w) / 2

        if self._direction == "down":
            y = 0.0
            _draw_rounded_rect_open_top(cr, x, y, cur_w, cur_h, cur_r)
        else:
            y = h - cur_h
            _draw_rounded_rect_open_bottom(cr, x, y, cur_w, cur_h, cur_r)

        cr.save()
        cr.clip()
        Gtk.Box.do_draw(self, cr)
        cr.restore()

        return True

def _ease_out_expo(t: float) -> float:
    """A snappy ease-out so width pops in faster than height."""
    if t >= 1.0:
        return 1.0
    return 1.0 - math.pow(2.0, -10.0 * t)

def _draw_rounded_rect_open_top(
    cr: cairo.Context,
    x: float, y: float,
    w: float, h: float,
    r: float,
):
    """Rounded rect with square top corners (flush with bar) and rounded bottom."""
    cr.move_to(x, y)
    cr.line_to(x + w, y)
    cr.line_to(x + w, y + h - r)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.line_to(x + r, y + h)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.line_to(x, y)
    cr.close_path()

def _draw_rounded_rect_open_bottom(
    cr: cairo.Context,
    x: float, y: float,
    w: float, h: float,
    r: float,
):
    """Rounded rect with rounded top corners and square bottom (flush with bar)."""
    cr.move_to(x + r, y)
    cr.line_to(x + w - r, y)
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.line_to(x + w, y + h)
    cr.line_to(x, y + h)
    cr.line_to(x, y + r)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()