from fabric.system_tray.service import SystemTray as FabricSystemTray, SystemTrayItem as FabricSystemTrayItem
from gi.repository import Gtk, GdkPixbuf
from fabric.core.service import Property
from fabric.utils.helpers import get_enum_member
from loguru import logger


class SystemTrayItem(FabricSystemTrayItem):
    @Property(Gtk.IconTheme, "readable")
    def icon_theme(self) -> Gtk.IconTheme:
        if not self._icon_theme:
            # copy default instead of using the shared instance
            self._icon_theme = Gtk.IconTheme.new()
            default = Gtk.IconTheme.get_default()
            # carry over existing search paths from the default theme
            for path in default.get_search_path():
                self._icon_theme.append_search_path(path)
            search_path = self.get_icon_theme_path()
            if search_path not in (None, ""):
                self._icon_theme.append_search_path(search_path)
        return self._icon_theme
    def get_preferred_icon_pixbuf(self, size=None, resize_method=GdkPixbuf.InterpType.BILINEAR):
        icon_name = self.icon_name
        attention_icon_name = self.attention_icon_name
        icon_pixmap = self.icon_pixmap
        attention_icon_pixmap = self.attention_icon_pixmap

        if self.status == "NeedsAttention" and (
            attention_icon_name is not None or attention_icon_pixmap is not None
        ):
            preferred_icon_name = attention_icon_name
            preferred_icon_pixmap = attention_icon_pixmap
        else:
            preferred_icon_name = icon_name
            preferred_icon_pixmap = icon_pixmap

        icon_theme = self.icon_theme
        icon_theme_sizes = (
            icon_theme.get_icon_sizes(preferred_icon_name)
            if preferred_icon_name is not None
            else []
        ) or []
        icon_theme_sizes.append(size if size is not None else 24)

        pixbuf = (
            preferred_icon_pixmap.as_pixbuf()
            if preferred_icon_pixmap is not None
            else icon_theme.load_icon(
                preferred_icon_name,
                max(icon_theme_sizes),
                Gtk.IconLookupFlags.FORCE_SIZE,
            )
            if preferred_icon_name is not None
            else None
        )
        return (
            pixbuf.scale_simple(
                size,
                size,
                get_enum_member(
                    GdkPixbuf.InterpType,
                    resize_method,
                    default=GdkPixbuf.InterpType.NEAREST,
                ),
            )
            if size is not None and pixbuf is not None
            else pixbuf
        )


class SystemTray(FabricSystemTray):
    def do_acquire_item_proxy_finish(self, bus_name, bus_path, proxy, result, *args):
        proxy = proxy.new_for_bus_finish(result)
        if not proxy:
            return logger.warning(
                f"[SystemTray] can't acquire proxy object for tray item with identifier {bus_name + bus_path}"
            )

        if not proxy.get_name_owner():
            return logger.warning(
                f"[SystemTray] skipping tray item with no name owner: {bus_name + bus_path}"
            )

        item = SystemTrayItem(proxy)
        item.removed.connect(lambda *args: self.remove_item(item))
        self.add_item(item)