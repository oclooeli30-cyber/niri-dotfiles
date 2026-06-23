from fabric.widgets.centerbox import CenterBox
from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.button import Button
from snippets import Icon
from typing import Callable
from gi.repository import Gdk

class QSButton(EventBox):
    def __init__(
        self,
        icon: Icon,
        label=None,
        on_activate: Callable | None = None,
        on_deactivate: Callable | None = None,
        menu_name: str | None = None,
        stack=None,
        style_classes: list | None = None,
        **kwargs,
    ):
        self.on_activate = on_activate
        self.on_deactivate = on_deactivate
        self._active = False
        self._menu_name = menu_name
        self._stack = stack
        self._label = label
        if stack and menu_name:
            self._chevron = Button(
                style_classes=["qs-button-chevron"],
                child=Icon(icon_name="chevron-right"),
                on_activate=lambda *_: self._stack.set_visible_child_name(self._menu_name),
                on_pressed=lambda *_: self._stack.set_visible_child_name(self._menu_name),
            )
        else:
            self._chevron = Box()

        self._main_box = Button(
            style_classes=["qs-button-label"] if menu_name else [],
            child=Box(
                orientation="h",
                spacing=6,
                children=[icon, label] if label else [icon],
            ),
            on_activate=lambda *_: self._callback(),
            on_pressed=lambda *_: self._callback(),
        )
        # if self._menu_name else Button(
        #         style_classes=["qs-button-label"] if menu_name else [],
        #         orientation="h",
        #         spacing=6,
        #         children=[icon, label] if label else [icon],
        #     )

        super().__init__(
            child=CenterBox(
                style_classes=style_classes or (["qs-button"] if not menu_name and label else ["qs-button-small"] if not label else []),
                start_children=self._main_box,
                end_children=self._chevron,
            ),
            h_expand=True,
            **kwargs,
        )
        self.add_events(
            Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.FOCUS_CHANGE_MASK
        )
        self.connect("enter-notify-event", self._on_hover_enter)
        self.connect("leave-notify-event", self._on_hover_leave)
        self.connect("focus-in-event", self._on_focus_in)
        self.connect("focus-out-event", self._on_focus_out)
        if not menu_name:
            self.set_can_focus(True)

        if not stack and not menu_name:
            self.connect("button-press-event", self._on_click)
            self.connect("key-press-event", self._on_key_press)

    def _on_hover_enter(self, _, event):
        if not self._menu_name:
            self.get_child().add_style_class("hover")
        return False

    def _on_hover_leave(self, _, event):
        if event.detail != Gdk.NotifyType.INFERIOR:
            if not self._menu_name:
                self.get_child().remove_style_class("hover")
        return False
    
    def _on_focus_in(self, _, event):
        if not self._menu_name:
            self.get_child().add_style_class("focus")
        return False

    def _on_focus_out(self, _, event):
        if not self._menu_name:
            self.get_child().remove_style_class("focus")
        return False

    def _on_click(self, _, event):
        self._callback()
        return True
    
    def _on_key_press(self, _, event):
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self._callback()
            return True
        return False
    
    def _callback(self):
        if self._active:
            if self.on_deactivate:
                self.on_deactivate(self)
        else:
            if self.on_activate:
                self.on_activate(self)
                
    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool):
        self._active = value
        inner = self.get_child()
        if inner:
            if value:
                inner.add_style_class("active")
            else:
                inner.remove_style_class("active")
        if value:
            self._main_box.add_style_class("active")
            self._chevron.add_style_class("active")
        else:
            self._main_box.remove_style_class("active")
            self._chevron.remove_style_class("active")