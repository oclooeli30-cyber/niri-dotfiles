import cairo
from gi.repository import Gtk
from fabric.widgets.box import Box
from snippets.animator import Animator

class DashReveal(Box):
    """
    A Cairo-drawn widget that animates the Dash in with a scale + fade effect.
    Scales from SCALE_START → 1.0 and fades from 0.0 → 1.0 simultaneously.

    Usage:
        reveal = DashReveal(child=your_main_box)
        reveal.open()            # animate in
        reveal.close(on_done=cb) # animate out, calls cb when finished
    """

    SCALE_START = 0.8

    def __init__(
        self,
        child: Gtk.Widget | None = None,
        open_bezier: tuple[float, float, float, float] = (0.22, 0.6, 0.36, 1.0),
        close_bezier: tuple[float, float, float, float] = (0.16, 1, 0.3, 1.0),
        open_duration: float = 0.35,
        close_duration: float = 0.22,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._progress = 0.0
        self._target = 0.0
        self._on_close_callbacks: list = []
        self.progress_cb = None

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
        self.show_all()

    def open(self):
        self._target = 1.0
        self.close_animator.pause()

        self.open_animator.pause()
        self.open_animator.min_value = self._progress
        self.open_animator.max_value = 1.0
        self.open_animator.value = self._progress
        self.open_animator._start_time = None
        self.open_animator.play()

    def close(self, on_done=None):
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

    @property
    def progress(self) -> float:
        return self._progress

    def do_draw(self, cr: cairo.Context) -> bool:
        p = self._progress
        if p <= 0.0:
            return True

        w = self.get_allocated_width()
        h = self.get_allocated_height()

        scale = self.SCALE_START + (1.0 - self.SCALE_START) * _ease_out_expo(p)

        cx = w / 2.0
        cy = h / 2.0

        cr.save()
        cr.translate(cx, cy)
        cr.scale(scale, scale)
        cr.translate(-cx, -cy)

        Gtk.Box.do_draw(self, cr)

        cr.restore()
        return True

def _ease_out_expo(t: float) -> float:
    if t >= 1.0:
        return 1.0
    return 1.0 - pow(2.0, -10.0 * t)