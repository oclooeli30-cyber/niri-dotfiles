from fabric.core.service import Property
from typing import Any
from ..base.window import WMWindow
from .window_layout import NiriWindowLayout


class NiriWindow(WMWindow):

    @Property(object, "readable", default_value=None)
    def layout(self) -> NiriWindowLayout:
        return self._property_helper_layout

    def __init__(self, service, **kwargs):
        self.__service = service
        self._property_helper_layout = NiriWindowLayout()
        super().__init__(**kwargs)

    def sort_key(self) -> tuple:
        try:
            pos = self._property_helper_layout.pos_in_scrolling_layout
            x = pos[0] if pos and isinstance(pos[0], (int, float)) else 0
            y = pos[1] if pos and isinstance(pos[1], (int, float)) else 0
            ws = self._property_helper_workspace_id or 0
            return (ws, x, y)
        except Exception:
            return (0, 0, 0)
        
    @property
    def data(self) -> dict:
        return {
            **super().data,
            "layout": self._property_helper_layout,
        }

    def sync(self, data: dict[str, Any]) -> None:
        data = dict(data)
        layout = data.pop("layout", None)

        if layout is not None:
            if isinstance(layout, dict):
                self._property_helper_layout.sync(layout)
            else:
                self._property_helper_layout.sync(layout.data)
            self.notify("layout")

        super().sync(data)

    def close(self) -> None:
        self.__service.send_command({"Action": {"CloseWindow": {"id": self.id}}})

    def focus(self) -> None:
        self.__service.send_command({"Action": {"FocusWindow": {"id": self.id}}})

    def toggle_fullscreen(self) -> None:
        self.__service.send_command({"Action": {"FullscreenWindow": {"id": self.id}}})

    def toggle_floating(self) -> None:
        self.__service.send_command({"Action": {"ToggleWindowFloating": {"id": self.id}}})
