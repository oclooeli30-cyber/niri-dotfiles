from fabric.core.service import Service, Signal, Property
from gi.repository import Gtk

class IconManager(Service):

    @Signal
    def icons_added(self, path: object): ...

    @Signal
    def icons_removed(self, path: object): ...

    @Property(object, "readable", default_value=None)
    def added_icons(self) -> list[str]:
        return self._property_helper_added_icons or []

    def __init__(self, **kwargs):
        self._property_helper_added_icons = []

        self._icon_theme = Gtk.IconTheme.get_default()
        super().__init__(**kwargs)

    def add_icons(self, path: str) -> None:
        self._icon_theme.append_search_path(path)
        self._property_helper_added_icons.append(path)
        self.notify("added-icons")
        self.emit("icons-added", path)

    def remove_icons(self, path: str) -> None:
        current = list(self._icon_theme.get_search_path())
        if path not in current:
            return
        current.remove(path)
        self._icon_theme.set_search_path(current)
        self._property_helper_added_icons.remove(path)
        self.notify("added-icons")
        self.emit("icons-removed", path)