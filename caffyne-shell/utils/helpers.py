import shutil
from gi.repository import GioUnix, Gtk, GdkPixbuf, GLib, Gio
from PIL import Image as PILImage, ImageEnhance, ImageFilter
import io
from snippets import enable_blur, set_blur_regions_from_widget

def popup_with_blur(menu: Gtk.Menu, event, accuracy: int = 1):
    blur_ctx = None

    def do_blur():
        nonlocal blur_ctx
        blur_ctx = enable_blur(menu)
        def do_set_regions():
            if blur_ctx:
                set_blur_regions_from_widget(blur_ctx, menu, accuracy, erode=0)
            return False
        GLib.timeout_add(50, do_set_regions)

    menu.show_all()
    menu.popup_at_pointer(event)
    GLib.idle_add(do_blur)

def executable_exists(executable_name):
    executable_path = shutil.which(executable_name)
    return bool(executable_path)

def get_app_icon_name(app_id: str) -> str | None:
    """
    Try to resolve an app icon name from a Niri app_id.
    Attempts several common transformations before giving up.
    Falls back to scanning all installed desktop files for a match.
    """

    def _icon_from_info(app_info):
        if not app_info:
            return None
        icon = app_info.get_icon()
        if not icon:
            return None
        if isinstance(icon, Gio.ThemedIcon):
            names = icon.get_names()
            if names:
                return names[0]
        elif isinstance(icon, Gio.FileIcon):
            f = icon.get_file()
            if f:
                return f.get_path()
        return None

    needle = app_id.lower()

    candidates = [
        app_id,
        needle,
        app_id.split(".")[-1],
        app_id.split(".")[-1].lower(),
        "-".join(app_id.split(".")).lower(),
    ]

    for candidate in candidates:
        try:
            result = _icon_from_info(GioUnix.DesktopAppInfo.new(candidate + ".desktop"))
            if result:
                return result
        except TypeError:
            continue

    for app in Gio.AppInfo.get_all():
        aid = (app.get_id() or "").lower().removesuffix(".desktop")
        if aid == needle:
            result = _icon_from_info(app)
            if result:
                return result

    for app in Gio.AppInfo.get_all():
        if hasattr(app, "get_string"):
            try:
                wm_class = (app.get_string("StartupWMClass") or "").lower()
            except TypeError:
                try:
                    wm_class = (app.get_string("StartupWMClass", None) or "").lower()
                except TypeError:
                    continue
            if wm_class == needle:
                result = _icon_from_info(app)
                if result:
                    return result

    for app in Gio.AppInfo.get_all():
        aid = (app.get_id() or "").lower()
        if needle in aid:
            result = _icon_from_info(app)
            if result:
                return result

    return None

def load_blurred_pixbuf(
    path: str,
    width: int,
    height: int,
    blur_radius=10,
    darken_factor=1.0,
):
    try:
        img = PILImage.open(path).convert("RGBA")
        img = img.resize((width, height))
        img = img.filter(ImageFilter.GaussianBlur(blur_radius))

        if darken_factor < 1.0:
            img = ImageEnhance.Brightness(img).enhance(darken_factor)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        loader = GdkPixbuf.PixbufLoader.new_with_type("png")
        loader.write(buf.read())
        loader.close()

        return loader.get_pixbuf()
    except Exception:
        return None
    
def load_scaled_pixbuf(path: str, width: int, height: int):
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(
            path, width, height, False
        )
    except Exception:
        return None
    
def load_cover_pixbuf(path: str, width: int, height: int):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)

    src_w = pixbuf.get_width()
    src_h = pixbuf.get_height()

    scale = max(width / src_w, height / src_h)

    scaled_w = int(src_w * scale)
    scaled_h = int(src_h * scale)

    scaled = pixbuf.scale_simple(
        scaled_w,
        scaled_h,
        GdkPixbuf.InterpType.BILINEAR,
    )

    x = (scaled_w - width) // 2
    y = (scaled_h - height) // 2

    return scaled.new_subpixbuf(x, y, width, height)