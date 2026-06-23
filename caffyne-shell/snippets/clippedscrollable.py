import math
import cairo
from typing import cast
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import GLib
class ClippingScrolledWindow(ScrolledWindow):
    """A ScrolledWindow that respects border-radius like `overflow: hidden`."""

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
        cr.close_path()

    def do_draw(self, cr: cairo.Context):
        cr.save()
        ClippingScrolledWindow.render_shape(
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
        ScrolledWindow.do_draw(self, cr)
        cr.restore()
        return True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connect("map", self._on_map)

    def _on_map(self, _):
        self.set_overlay_scrolling(False)
        self.set_overlay_scrolling(True)