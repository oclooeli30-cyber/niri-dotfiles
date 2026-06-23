from ..base.keyboard import WMKeyboardLayouts


class HyprlandKeyboardLayouts(WMKeyboardLayouts):

    def __init__(self, service, **kwargs):
        self.__service = service
        super().__init__(**kwargs)

    def sync(self, data: dict) -> None:
        if "names" in data:
            self._property_helper_names = data["names"]
            self.notify("names", "current-name")
        if "current_idx" in data:
            self._property_helper_current_idx = data["current_idx"]
            self.notify("current-idx", "current-name")

    def switch_layout(self, layout: str) -> None:
        # Hyprland: switchxkblayout <device> next|prev|<index>
        self.__service.send_command(f"switchxkblayout all {layout}")
