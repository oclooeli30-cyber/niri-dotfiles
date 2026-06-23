from ..base.keyboard import WMKeyboardLayouts


class NiriKeyboardLayouts(WMKeyboardLayouts):

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
        """
        layout can be:
          "next" / "prev"  — cycle through layouts
          "0", "1", ...    — switch to layout by index
        """
        lower = layout.lower()
        if lower == "next":
            niri_layout = "Next"
        elif lower == "prev":
            niri_layout = "Prev"
        else:
            try:
                niri_layout = {"Index": int(layout)}
            except ValueError:
                # Last resort: try treating it as a named action (Next/Prev)
                niri_layout = layout

        self.__service.send_command(
            {"Action": {"SwitchLayout": {"layout": niri_layout}}}
        )