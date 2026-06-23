from fabric.widgets.box import Box
from fabric.widgets.image import Image
from services.singletons import wm
from utils.helpers import get_app_icon_name
from snippets import ScrollingLabel

FALLBACK_ICON = "application-x-executable-symbolic"
FALLBACK_TITLE = "Desktop"


def _set_icon(img: Image, value: str, size: int) -> None:
    if value.startswith("/"):
        img.set_from_file(value)
    else:
        img.set_from_icon_name(value, size)


class NiriClientTitle(Box):
    def __init__(self, monitor_id, vertical, variant, **kwargs):
        self.icon = Image(
            style_classes=["icon"],
            icon_name=FALLBACK_ICON,
            icon_size=18,
        )
        self.label = ScrollingLabel(ellipsization="end", max_width=120, pixels_per_second=100)

        wm.active_window.connect(
            "notify::app-id",
            lambda obj, _: _set_icon(
                self.icon,
                get_app_icon_name(obj.app_id) or FALLBACK_ICON,
                18,
            ),
        )
        wm.active_window.connect(
            "notify::title",
            lambda obj, _: self.label.set_label(obj.title or FALLBACK_TITLE),
        )

        _set_icon(
            self.icon,
            get_app_icon_name(wm.active_window.app_id) or FALLBACK_ICON,
            18,
        )
        self.label.set_label(wm.active_window.title or FALLBACK_TITLE)

        super().__init__(
            style_classes=["bar-button"],
            spacing=4,
            children=[self.icon, self.label],
            **kwargs,
        )

