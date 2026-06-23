from gi.repository import GLib, Gtk
from .clippedscrollable import ClippingScrolledWindow

class AnimatedScroll(ClippingScrolledWindow):
    def __init__(self, fade_distance: int = 12, **kwargs):
        self._fade_distance = fade_distance
        self._idle_id = None
        super().__init__(**kwargs)

        adj = self.get_vadjustment()
        adj.connect("value-changed", lambda a: self._on_scroll(a))
        adj.connect("changed", lambda *_: self._schedule_refresh())
        self.connect("map", lambda *_: self._schedule_refresh())

    def set_child(self, widget):
        super().add(widget)
        self._watch_container(widget)
        if isinstance(widget, Gtk.Stack):
            widget.connect("notify::visible-child", lambda *_: self._schedule_refresh())
            for child in widget.get_children():
                self._watch_container(child)
        self._schedule_refresh()

    def _watch_container(self, widget):
        if isinstance(widget, Gtk.Container):
            widget.connect("add", lambda *_: self._schedule_refresh())
            widget.connect("remove", lambda *_: self._schedule_refresh())

    def _get_item_container(self):
        viewport = self.get_child()
        if not viewport:
            return None
        content = viewport.get_child() if hasattr(viewport, "get_child") else None
        if not content:
            return None
        if isinstance(content, Gtk.Stack):
            visible = content.get_visible_child()
            return visible if isinstance(visible, Gtk.Container) else None
        return content

    def _schedule_refresh(self):
        if self._idle_id is not None:
            GLib.source_remove(self._idle_id)
        self._idle_id = GLib.idle_add(self._idle_refresh)

    def _idle_refresh(self):
        self._idle_id = None
        adj = self.get_vadjustment()
        self._on_scroll(adj)
        return GLib.SOURCE_REMOVE

    def _on_scroll(self, adjustment):
        content = self._get_item_container()
        if not content:
            return

        viewport_top = adjustment.get_value()
        viewport_bottom = viewport_top + adjustment.get_page_size()
        fade = self._fade_distance

        for child in content.get_children():
            alloc = child.get_allocation()
            child_top = alloc.y
            child_bottom = child_top + alloc.height

            if child_bottom < viewport_top:
                _set_fade(child, "top")
            elif child_top > viewport_bottom:
                _set_fade(child, "bottom")
            elif child_bottom >= viewport_top and child_bottom < viewport_top + fade and viewport_top > fade:
                _set_fade(child, "top")
            elif child_top <= viewport_bottom and child_top > viewport_bottom - fade:
                _set_fade(child, "bottom")
            else:
                _set_fade(child, None)


def _set_fade(widget, direction: str | None):
    widget.get_style_context().add_class("animated-scroll-child")
    ctx = widget.get_style_context()
    if direction == "top":
        ctx.add_class("fade-out-top")
        ctx.remove_class("fade-in")
        ctx.remove_class("fade-out-bottom")
    elif direction == "bottom":
        ctx.add_class("fade-out-bottom")
        ctx.remove_class("fade-in")
        ctx.remove_class("fade-out-top")
    else:
        ctx.add_class("fade-in")
        ctx.remove_class("fade-out-top")
        ctx.remove_class("fade-out-bottom")


class AnimatedScrollH(ClippingScrolledWindow):
    def __init__(self, fade_distance: int = 25, **kwargs):
        self._fade_distance = fade_distance
        self._idle_id = None
        super().__init__(**kwargs)

        adj = self.get_hadjustment()
        adj.connect("value-changed", lambda a: self._on_scroll(a))
        adj.connect("changed", lambda *_: self._schedule_refresh())
        self.connect("map", lambda *_: self._schedule_refresh())

    def set_child(self, widget):
        super().add(widget)
        self._watch_container(widget)
        self._schedule_refresh()

    def _watch_container(self, widget):
        if isinstance(widget, Gtk.Container):
            widget.connect("add", lambda *_: self._schedule_refresh())
            widget.connect("remove", lambda *_: self._schedule_refresh())

    def _schedule_refresh(self):
        if self._idle_id is not None:
            GLib.source_remove(self._idle_id)
        self._idle_id = GLib.idle_add(self._idle_refresh)

    def _idle_refresh(self):
        self._idle_id = None
        adj = self.get_hadjustment()
        self._on_scroll(adj)
        return GLib.SOURCE_REMOVE

    def _on_scroll(self, adjustment):
        viewport = self.get_child()
        if not viewport:
            return
        content = viewport.get_child() if hasattr(viewport, "get_child") else None
        if not content:
            return

        viewport_left  = adjustment.get_value()
        viewport_right = viewport_left + adjustment.get_page_size()
        fade = self._fade_distance

        for child in content.get_children():
            alloc = child.get_allocation()
            child_left  = alloc.x
            child_right = child_left + alloc.width

            if child_right < viewport_left:
                _set_fade_h(child, "left")
            elif child_left > viewport_right:
                _set_fade_h(child, "right")
            elif child_right >= viewport_left and child_right < viewport_left + fade and viewport_left > fade:
                _set_fade_h(child, "left")
            elif child_left <= viewport_right and child_left > viewport_right - fade:
                _set_fade_h(child, "right")
            else:
                _set_fade_h(child, None)


def _set_fade_h(widget, direction: str | None):
    widget.get_style_context().add_class("animated-scroll-child-h")
    ctx = widget.get_style_context()
    if direction == "left":
        ctx.add_class("fade-out-left")
        ctx.remove_class("fade-in-h")
        ctx.remove_class("fade-out-right")
    elif direction == "right":
        ctx.add_class("fade-out-right")
        ctx.remove_class("fade-in-h")
        ctx.remove_class("fade-out-left")
    else:
        ctx.add_class("fade-in-h")
        ctx.remove_class("fade-out-left")
        ctx.remove_class("fade-out-right")