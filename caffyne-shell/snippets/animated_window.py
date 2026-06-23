import math
import cairo
from typing import Literal, cast
from fabric.widgets.box import Box
from fabric.widgets.wayland import WaylandWindow as Window
from snippets.animator import Animator, cubic_bezier
from gi.repository import Gtk

AnimationType = Literal["scale_up", "scale_down", "scale_left", "scale_right"]

class ClippingBox(Box):
    @staticmethod
    def render_shape(cr: cairo.Context, width: int, height: int, radius: int = 0):
        cr.move_to(radius, 0)
        cr.line_to(width - radius, 0)
        cr.arc(width - radius, radius, radius, -(math.pi / 2), 0)
        cr.line_to(width, height - radius)
        cr.arc(width - radius, height - radius, radius, 0, (math.pi / 2))
        cr.line_to(radius, height)
        cr.arc(radius, height - radius, radius, (math.pi / 2), math.pi)
        cr.line_to(0, radius)
        cr.arc(radius, radius, radius, math.pi, (3 * (math.pi / 2)))
        return cr.close_path()

    def do_draw(self, cr: cairo.Context):
        cr.save()
        ClippingBox.render_shape(
            cr,
            self.get_allocated_width(),
            self.get_allocated_height(),
            cast(
                int,
                self.get_style_context().get_property(
                    "border-radius", self.get_state_flags()
                ),
            ),
        )
        cr.clip()
        Box.do_draw(self, cr)
        cr.restore()
        return True
class LimitBox(Gtk.Box):
    def __init__(self, max_width: int = -1, max_height: int = -1, **kwargs):
        super().__init__(**kwargs)
        self.max_width = max_width
        self.max_height = max_height

    def do_size_allocate(self, allocation):
        if self.max_width >= 0:
            allocation.width = min(self.max_width, allocation.width)
        if self.max_height >= 0:
            allocation.height = min(self.max_height, allocation.height)
        return Gtk.Box.do_size_allocate(self, allocation)

class AnimatedWindow(Window):
    def __init__(
        self,
        animation_type: AnimationType = "scale_up",
        duration: float = 0.3,
        bezier_curve: tuple[float, float, float, float] = (0.4, 0.0, 0.2, 1.0),
        child=None,
        **kwargs,
    ):
        self._animation_type = animation_type
        self._duration = duration
        self._bezier_curve = bezier_curve
        self._target_visible = False
        self._animator: Animator | None = None
        self._is_vertical = animation_type in ("scale_up", "scale_down")

        self._clip_box = ClippingBox(orientation="v" if self._is_vertical else "h")
        if child:
            self._clip_box.add(child)

        self._limit_box = LimitBox()
        self._limit_box.add(self._clip_box)

        kwargs["child"] = self._limit_box
        kwargs["visible"] = False

        super().__init__(**kwargs)

    def _get_natural_size(self) -> int:
        if self._is_vertical:
            _, natural = self._clip_box.get_preferred_height()
        else:
            _, natural = self._clip_box.get_preferred_width()
        return natural

    def _setup_animator(self, natural_size: int):
        if self._animator:
            self._animator.pause()
        self._animator = Animator(
            timing_function=lambda progress: cubic_bezier(*self._bezier_curve, progress),
            duration=self._duration,
            min_value=0.0,
            max_value=float(natural_size),
            tick_widget=self._limit_box,
        )
        self._animator.connect("notify::value", self._on_animator_value)
        self._animator.connect("finished", self._on_animator_finished)

    def _on_animator_value(self, animator, _):
        v = int(animator.value)
        if self._is_vertical:
            self._limit_box.max_height = v
        else:
            self._limit_box.max_width = v
        self._limit_box.queue_resize()

    def _on_animator_finished(self, animator):
        if not self._target_visible:
            super().set_visible(False)
            self._limit_box.max_height = -1
            self._limit_box.max_width = -1

    def _do_open(self):
        natural = self._get_natural_size()
        if natural <= 1:
            super().set_visible(True)
            return

        self._setup_animator(natural)
        self._animator.min_value = 0.0
        self._animator.max_value = float(natural)
        self._animator.value = 0.0

        if self._is_vertical:
            self._limit_box.max_height = 0
        else:
            self._limit_box.max_width = 0

        super().set_visible(True)
        self._animator.play()

    def _do_close(self):
        natural = self._get_natural_size()
        if natural <= 1:
            super().set_visible(False)
            return

        self._setup_animator(natural)
        self._animator.min_value = float(natural)
        self._animator.max_value = 0.0
        self._animator.value = float(natural)
        self._animator.play()

    def set_visible(self, value: bool):
        if self._target_visible == value:
            return
        self._target_visible = value
        if value:
            self._do_open()
        else:
            self._do_close()

    def toggle(self):
        self.set_visible(not self._target_visible)