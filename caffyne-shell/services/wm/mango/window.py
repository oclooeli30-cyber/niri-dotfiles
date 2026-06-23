from ..base.window import WMWindow
from .workspace import _synth_workspace_id


class MangoWindow(WMWindow):
    def __init__(self, service, **kwargs):
        self.__service = service
        super().__init__(**kwargs)

    def sync(self, data: dict) -> None:
        tags: list[int] = data.get("tags", [0])
        raw_tag = tags[0] if tags else 0
        monitor_name = data.get("monitor", "")

        super().sync({
            "id": data["id"],
            "title": data.get("title", ""),
            "app_id": data.get("appid", ""),
            "pid": data.get("pid", 0),
            "workspace_id": _synth_workspace_id(monitor_name, raw_tag),
            "is_focused": data.get("is_focused", False),
            "is_floating": data.get("is_floating", False),
        })

    def sort_key(self) -> tuple:
        return (self.workspace_id, 0, 0)

    def close(self) -> None:
        self.__service.send_command(f"dispatch killclient,id:{self.id}")

    def focus(self) -> None:
        self.__service.send_command(f"dispatch focusclient,id:{self.id}")

    def toggle_fullscreen(self) -> None:
        self.__service.send_command(f"dispatch togglefullscreen,id:{self.id}")

    def toggle_floating(self) -> None:
        self.__service.send_command(f"dispatch togglefloating,id:{self.id}")