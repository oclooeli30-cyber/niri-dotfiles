from fabric.core.service import Service, Property


class WMKeyboardLayouts(Service):
    """Base class for keyboard layout management."""

    @Property(object, "readable", default_value=None)
    def names(self) -> list:
        return self._property_helper_names or []

    @Property(int, "readable", default_value=-1)
    def current_idx(self) -> int:
        return self._property_helper_current_idx

    @Property(str, "readable", default_value="")
    def current_name(self) -> str:
        names = self._property_helper_names or []
        idx = self._property_helper_current_idx
        if not names or idx is None or idx < 0:
            return ""
        return names[idx]

    def __init__(self, **kwargs):
        self._property_helper_names = []
        self._property_helper_current_idx = -1
        super().__init__(**kwargs)

    def switch_layout(self, layout: str) -> None:
        """Switch to a named layout. Override in subclass."""
        raise NotImplementedError
