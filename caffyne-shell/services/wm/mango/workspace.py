from ..base.workspace import WMWorkspace


def _synth_workspace_id(monitor_name: str, tag_index: int) -> int:
    return hash((monitor_name, tag_index)) & 0x7FFFFFFF


class MangoWorkspace(WMWorkspace):
    def __init__(self, service, **kwargs):
        # Initialize the GObject first
        super().__init__(**kwargs)
        # Store the service privately
        self.__service = service

    def sync(
        self,
        monitor_name: str,
        tag: dict,
        active_tags: list[int],
        is_focused_monitor: bool,
        active_window_id: int = 0, # Accept the ID here
    ) -> None:
        idx: int = tag["index"]
        is_active = idx in active_tags
        is_focused = is_active and is_focused_monitor

        # super().sync updates the internal property helpers 
        # and triggers the necessary 'notify' signals.
        super().sync(
            {
                "id": _synth_workspace_id(monitor_name, idx),
                "idx": idx,
                "name": str(idx),
                "output": monitor_name,
                "is_active": is_active,
                "is_focused": is_focused,
                "active_window_id": active_window_id, 
            }
        )
    def switch_to(self) -> None:
        self.__service.send_command(
            f"dispatch view,{self.idx},0,{self.output}"
        )