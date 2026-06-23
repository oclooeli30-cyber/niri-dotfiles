from fabric.core.service import Service, Property, Signal


class WMWorkspace(Service):
    """
    Base class for a workspace across all supported WMs.

    All properties here are expected to be available on every backend.
    """

    @Signal
    def destroyed(self): ...

    @Property(int, "readable", default_value=-1)
    def id(self) -> int:
        return self._property_helper_id

    @Property(int, "readable", default_value=-1)
    def idx(self) -> int:
        return self._property_helper_idx

    @Property(str, "readable", default_value="")
    def name(self) -> str:
        return self._property_helper_name or ""

    @Property(str, "readable", default_value="")
    def output(self) -> str:
        return self._property_helper_output or ""

    @Property(bool, "readable", default_value=False)
    def is_active(self) -> bool:
        return self._property_helper_is_active or False

    @Property(bool, "readable", default_value=False)
    def is_focused(self) -> bool:
        return self._property_helper_is_focused or False

    @Property(int, "readable", default_value=-1)
    def active_window_id(self) -> int:
        return self._property_helper_active_window_id

    def __init__(self, **kwargs):
        self._property_helper_id = -1
        self._property_helper_idx = -1
        self._property_helper_name = ""
        self._property_helper_output = ""
        self._property_helper_is_active = False
        self._property_helper_is_focused = False
        self._property_helper_active_window_id = -1
        super().__init__(**kwargs)

    def sync(self, data: dict) -> None:
        mapping = {
            "id": "id",
            "idx": "idx",
            "name": "name",
            "output": "output",
            "is_active": "is-active",
            "is_focused": "is-focused",
            "active_window_id": "active-window-id",
        }
        for key, notify_name in mapping.items():
            if key in data:
                setattr(self, f"_property_helper_{key}", data[key])
                self.notify(notify_name)

    def switch_to(self) -> None:
        raise NotImplementedError
