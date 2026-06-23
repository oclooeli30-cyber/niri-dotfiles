import cairo
from gi.repository import Gtk, GLib
from fabric.widgets.widget import Widget
from fabric.core.service import Property

class Graph(Gtk.DrawingArea, Widget):
    @Property(list, "read-write")
    def data(self) -> list:
        return self._data

    @data.setter
    def data(self, value: list) -> None:
        self._data = value

    def __init__(
        self,
        data: list[float] | None = None,
        min_value: float = 0.0,
        max_value: float = 100.0,
        line_width: float = 2.0,
        fill: bool = True,
        smooth: bool = True,
        dynamic: bool = False,
        size: tuple[int, int] = (200, 100),
        animate_duration: int = 300,
        **kwargs,
    ):
        Gtk.DrawingArea.__init__(self)
        Widget.__init__(self, **kwargs)

        self._data = data if data is not None else []
        self._display_data = list(self._data)
        self._min_value = min_value
        self._max_value = max_value
        self._line_width = line_width
        self._fill = fill
        self._smooth = smooth
        self._dynamic = dynamic
        self._scroll_start_time = None
        self._pending: list[float] = []
        self._animation_id = None

        self.set_size_request(size[0], size[1])
        self.connect("draw", self._on_draw)

    def push(self, value: float) -> None:
        self._pending.append(value)
        self._data = self._display_data + self._pending

        if self._animation_id is None:
            self._scroll_start_time = GLib.get_monotonic_time()
            self._animation_id = GLib.timeout_add(16, self._tick)

    def _tick(self) -> bool:
        if not self._pending:
            self._animation_id = None
            self._scroll_start_time = None
            return False

        elapsed_ms = (GLib.get_monotonic_time() - self._scroll_start_time) / 1000

        if elapsed_ms >= 1000:
            next_val = self._pending.pop(0)
            self._display_data = self._display_data[1:] + [next_val]
            self._data = self._display_data + self._pending
            self._scroll_start_time = GLib.get_monotonic_time()

        self.queue_draw()
        return True

    def _on_draw(self, widget, cr: cairo.Context):
        alloc = self.get_allocation()
        width, height = alloc.width, alloc.height
        color = self.get_style_context().get_color(Gtk.StateFlags.NORMAL)

        if self._pending and self._scroll_start_time is not None:
            elapsed_ms = (GLib.get_monotonic_time() - self._scroll_start_time) / 1000
            t = min(elapsed_ms / 1000, 1.0)
            incoming = self._display_data[-1] + (self._pending[0] - self._display_data[-1]) * t
            render_data = self._display_data + [incoming]
            scroll_frac = t
        else:
            render_data = self._display_data
            scroll_frac = 0.0

        if not render_data or len(render_data) < 2:
            return

        if self._dynamic:
            min_val = min(render_data)
            max_val = max(render_data)
            value_range = max_val - min_val
            min_val -= value_range * 0.1
            max_val += value_range * 0.1
        else:
            min_val = self._min_value
            max_val = self._max_value

        if max_val - min_val == 0:
            max_val = min_val + 1

        num_stable = len(self._display_data)
        x_step = width / (num_stable - 1)
        scroll_offset = x_step * scroll_frac

        def value_to_y(v):
            return height - ((v - min_val) / (max_val - min_val)) * height

        points = [
            (i * x_step - scroll_offset, value_to_y(v))
            for i, v in enumerate(render_data)
        ]

        def draw_curve(cr, points):
            cr.move_to(points[0][0], points[0][1])
            if self._smooth and len(points) > 2:
                for i in range(len(points) - 1):
                    x0, y0 = points[i]
                    x1, y1 = points[i + 1]
                    x_prev, y_prev = points[i - 1] if i > 0 else (x0, y0)
                    x_next, y_next = points[i + 2] if i < len(points) - 2 else (x1, y1)
                    cp1x = x0 + (x1 - x_prev) / 6
                    cp1y = y0 + (y1 - y_prev) / 6
                    cp2x = x1 - (x_next - x0) / 6
                    cp2y = y1 - (y_next - y0) / 6
                    cr.curve_to(cp1x, cp1y, cp2x, cp2y, x1, y1)
            else:
                for x, y in points[1:]:
                    cr.line_to(x, y)

        cr.rectangle(0, 0, width, height)
        cr.clip()
        cr.save()

        if self._fill:
            cr.move_to(0, height)
            cr.line_to(max(points[0][0], 0), points[0][1])
            draw_curve(cr, points)
            cr.line_to(points[-1][0], height)
            cr.line_to(0, height)
            cr.close_path()
            gradient = cairo.LinearGradient(0, height, 0, 0)
            gradient.add_color_stop_rgba(0, color.red, color.green, color.blue, 0.6)
            gradient.add_color_stop_rgba(1, color.red, color.green, color.blue, 0)
            cr.set_source(gradient)
            cr.fill()

        draw_curve(cr, points)
        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        cr.set_line_width(self._line_width)
        cr.set_line_cap(cairo.LineCap.ROUND)
        cr.set_line_join(cairo.LineJoin.ROUND)
        cr.stroke()

        cr.restore()