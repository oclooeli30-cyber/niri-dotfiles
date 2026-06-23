from ..base.keyboard import WMKeyboardLayouts


class MangoKeyboardLayouts(WMKeyboardLayouts):
    def __init__(self, service, **kwargs):
        self.__service = service
        super().__init__(**kwargs)

    def sync(self, data: dict) -> None:
        # 1. Extract the new layout string from the incoming data
        layout_name: str = data.get("keyboardlayout", "")

        # 2. Get the current list of names (handling the empty list case)
        names = list(self.names) if self.names else []
        
        # 3. Add the layout to our known list if it's new
        if layout_name and layout_name not in names:
            names.append(layout_name)
            self._property_helper_names = names
            # Notify that names changed, and current-name follows
            self.notify("names", "current-name")

        # 4. Update the current index
        current_idx = names.index(layout_name) if layout_name in names else 0
        if current_idx != self._property_helper_current_idx:
            self._property_helper_current_idx = current_idx
            # Notify that current-idx changed, and current-name follows
            self.notify("current-idx", "current-name")

    def switch_layout(self, layout: str) -> None:
        # mango dispatch: "next" cycles forward, layout name sets directly.
        self.__service.send_command(f"dispatch switchkblayout,{layout}")