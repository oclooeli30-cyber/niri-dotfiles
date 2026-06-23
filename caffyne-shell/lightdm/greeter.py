import gi, os, pwd, datetime, threading
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("LightDM", "1")
from gi.repository import Gtk, Gdk, GLib, LightDM

from fabric.widgets.x11 import X11Window
from fabric.widgets.entry import Entry
from fabric.widgets.box import Box
from fabric.widgets.overlay import Overlay
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.label import Label
from fabric.widgets.image import Image
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.button import Button
from fabric import Application
from fabric.utils import get_relative_path
from icon import Icon
from gi.repository import GioUnix, Gtk, GdkPixbuf, GLib
from PIL import Image as PILImage, ImageFilter
import io


def load_blurred_pixbuf(path: str, width: int, height: int, blur_radius=10):
    try:
        img = PILImage.open(path).convert("RGBA")
        img = img.resize((width, height))
        img = img.filter(ImageFilter.GaussianBlur(blur_radius))

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


class LightDMClient:
    """
    Wraps LightDM.Greeter and exposes a simple callback-based API that mirrors
    the feel of the old GreetdClient without the raw socket work.

    Auth flow
    ---------
    1. Call authenticate(username, on_prompt, on_complete)
    2. LightDM fires show-prompt  → on_prompt(text, prompt_type) is called
       → you call respond(secret) from inside that callback
    3. LightDM fires authentication-complete
       → on_complete(authenticated: bool) is called
    4. If authenticated, call start_session(session_key)
    """

    def __init__(self):
        self._greeter = LightDM.Greeter.new()
        self._greeter.connect("show-prompt",            self._on_show_prompt)
        self._greeter.connect("show-message",           self._on_show_message)
        self._greeter.connect("authentication-complete",self._on_auth_complete)

        # connect_to_daemon_sync() raises on failure – let it propagate so the
        # caller knows immediately that something is wrong.
        self._greeter.connect_to_daemon_sync()

        self._on_prompt_cb   = None   # (text: str, prompt_type: LightDM.PromptType) -> None
        self._on_message_cb  = None   # (text: str, msg_type: LightDM.MessageType)   -> None
        self._on_complete_cb = None   # (authenticated: bool)                         -> None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def authenticate(self, username: str, on_prompt, on_complete, on_message=None):
        """Start an authentication attempt for *username*."""
        self._on_prompt_cb   = on_prompt
        self._on_complete_cb = on_complete
        self._on_message_cb  = on_message
        self._greeter.authenticate(username)

    def respond(self, secret: str):
        """Feed the answer to the current PAM prompt."""
        self._greeter.respond(secret)

    def cancel(self):
        self._greeter.cancel_authentication()

    def start_session(self, session_key: str) -> bool:
        """
        Launch the session.  Returns True on success.
        session_key comes from LightDM.Session.get_key(), e.g. "hyprland".
        """
        return self._greeter.start_session_sync(session_key)

    # ------------------------------------------------------------------
    # LightDM signal handlers  (all called on the GTK main loop – safe)
    # ------------------------------------------------------------------

    def _on_show_prompt(self, greeter, text: str, prompt_type):
        if self._on_prompt_cb:
            self._on_prompt_cb(text, prompt_type)

    def _on_show_message(self, greeter, text: str, msg_type):
        if self._on_message_cb:
            self._on_message_cb(text, msg_type)

    def _on_auth_complete(self, greeter):
        if self._on_complete_cb:
            authenticated = greeter.get_is_authenticated()
            self._on_complete_cb(authenticated)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_human_users() -> list[str]:
    no_login = {"/usr/sbin/nologin", "/sbin/nologin", "/bin/false", "/usr/bin/false"}
    return sorted(
        p.pw_name for p in pwd.getpwall()
        if p.pw_uid >= 1000 and p.pw_shell not in no_login
    )

def get_sessions() -> list[dict]:
    """
    Ask LightDM for the available sessions.
    Falls back to a bare /bin/bash entry if the list is empty (e.g. in a test env).
    """
    sessions = [
        {"name": s.get_name(), "key": s.get_key()}
        for s in LightDM.get_sessions()
    ]
    return sessions or [{"name": "Bash (fallback)", "key": ""}]


# ---------------------------------------------------------------------------
# Re-usable dropdown widget  (unchanged from greetd version)
# ---------------------------------------------------------------------------

class DropdownPicker(Button):
    def __init__(self, items: list[str], on_change, **kwargs):
        self._items    = items
        self._on_change = on_change
        self._selected  = 0

        self._menu = Gtk.Menu()
        for i, item in enumerate(items):
            mi = Gtk.MenuItem(label=item)
            mi.connect("activate", lambda _, idx=i: self._select(idx))
            mi.show()
            self._menu.append(mi)

        super().__init__(
            label=items[0] if items else "",
            on_pressed=self._on_pressed,
            **kwargs,
        )

    def _on_pressed(self, _button):
        self._menu.popup_at_pointer(None)

    def _select(self, idx: int):
        self._selected = idx
        self.set_label(self._items[idx])
        self._on_change(idx)

    @property
    def selected_index(self) -> int:
        return self._selected


# ---------------------------------------------------------------------------
# Per-monitor greeter window
# ---------------------------------------------------------------------------

class GreeterWindow(X11Window):
    def __init__(
        self,
        client: LightDMClient,
        users: list[str],
        sessions: list[dict],
        monitor: Gdk.Monitor,
        monitor_idx: int,
        is_primary: bool,
    ):
        self._client          = client
        self._users           = users
        self._sessions        = sessions
        self._current_user    = users[0] if users else ""
        self._current_session = sessions[0]
        self._auth_pending    = False   # guard against double-submit

        geo = monitor.get_geometry()
        self._geo = geo

        # ── Clock ────────────────────────────────────────────────────────────
        self.clock_progress = CircularProgressBar(
            style_classes=["progress-bar"],
            start_angle=270,
            end_angle=630,
            size=(138, 138),
            line_width=6,
            min_value=0,
            max_value=60,
            value=0,
        )
        self.clock_label = Label(style="font-size: 32px;")
        self.clock_circle = Overlay(
            child=Box(
                style_classes=["lockscreen-clock"],
                h_expand=False,
                h_align="center",
                children=self.clock_progress,
            ),
            overlays=self.clock_label,
        )

        # ── Pickers ──────────────────────────────────────────────────────────
        self._user_picker = DropdownPicker(
            items=self._users,
            on_change=self._on_user_change,
            style_classes=["picker"],
        )
        self._session_picker = DropdownPicker(
            items=[s["name"] for s in self._sessions],
            on_change=self._on_session_change,
            style_classes=["picker"],
        )

        # ── Entry + error ─────────────────────────────────────────────────────
        self._entry_field = Entry(
            password=True,
            on_activate=self._on_activate,
        )
        self._error_label = Label(
            label="",
            style_classes=["greeter-error"],
        )
        entry_box = Box(
            spacing=6,
            style_classes=["lockscreen-entry-box"],
            children=[Icon(icon_name="key-duotone", icon_size=16), self._entry_field],
        )
        entry_row = Box(
            spacing=6,
            children=[
                entry_box,
                Button(
                    style_classes=["lockscreen-submit-button"],
                    child=Icon(icon_name="caret-double-right-duotone", icon_size=16),
                    on_pressed=lambda _: self._on_activate(self._entry_field),
                ),
            ],
        )

        # ── Background ───────────────────────────────────────────────────────
        self._bg_image = Image(
            pixbuf=load_scaled_pixbuf(
                path="/usr/share/backgrounds/wallpaper",
                width=geo.width,
                height=geo.height,
            )
        )

        # ── Layout ───────────────────────────────────────────────────────────
        layout = Overlay(
            child=self._bg_image,
            overlays=CenterBox(
                orientation="v",
                h_expand=True,
                h_align="center",
                start_children=[self.clock_circle],
                center_children=[
                    Box(
                        orientation="v",
                        spacing=12,
                        h_align="center",
                        children=[
                            self._user_picker,
                            self._session_picker,
                            entry_row,
                            self._error_label,
                        ],
                    )
                ],
                style="margin: 200px 0px;",
            ),
        )

        # ── X11Window init ───────────────────────────────────────────────────
        # type_hint="splashscreen"  → above everything, no WM decorations,
        #                             no taskbar entry, accepts input
        # geometry="center"        → GTK centres the window for us
        # size                     → fullscreen dimensions for this monitor
        # sticky=True              → visible on all virtual desktops
        # layer="top"              → keep_above hint
        # focusable=True           → LightDM needs keyboard events
        super().__init__(
            type_hint="splashscreen",
            geometry="center",
            size=(geo.width, geo.height),
            layer="top",
            sticky=True,
            focusable=True,
            decorated=False,
            resizable=False,
            taskbar_hint=False,
            child=layout,
            visible=True,
            all_visible=True,
        )

        # Only the primary monitor window handles auth input
        if is_primary:
            # move to the right monitor (X11Window defaults to primary)
            self.move(geo.x, geo.y)
            self.connect("realize", self._on_realize)
            GLib.timeout_add(1000, self._update_time)
            self._update_time()
            threading.Thread(target=self._load_wallpaper, daemon=True).start()
        else:
            # Secondary monitors: show clock + blurred wallpaper, no input widgets
            self._entry_field.set_sensitive(False)
            self.move(geo.x, geo.y)
            GLib.timeout_add(1000, self._update_time)
            self._update_time()
            threading.Thread(target=self._load_wallpaper, daemon=True).start()

    def _on_realize(self, _widget):
        # Grab keyboard so the WM can't steal keystrokes before the user types
        self.steal_input()
        self._entry_field.grab_focus()

    # ── Wallpaper ─────────────────────────────────────────────────────────────

    def _load_wallpaper(self):
        pixbuf = load_blurred_pixbuf(
            path="/usr/share/backgrounds/wallpaper",
            width=self._geo.width,
            height=self._geo.height,
        )
        GLib.idle_add(self._bg_image.set_from_pixbuf, pixbuf)

    # ── Clock ─────────────────────────────────────────────────────────────────

    def _update_time(self):
        now = datetime.datetime.now()
        self.clock_label.set_label(now.strftime("%H\n%M"))
        self.clock_progress.value = int(now.strftime("%S"))
        return True  # keep GLib.timeout_add firing

    # ── Picker callbacks ──────────────────────────────────────────────────────

    def _on_user_change(self, idx: int):
        self._current_user = self._users[idx]
        self._entry_field.set_text("")
        self._error_label.set_label("")

    def _on_session_change(self, idx: int):
        self._current_session = self._sessions[idx]

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _show_error(self, msg: str):
        self._error_label.set_label(msg)
        self._entry_field.set_text("")
        self._auth_pending = False

    def _on_activate(self, entry: Entry, *_):
        if self._auth_pending:
            return

        password = (entry.get_text() or "").strip()
        self._error_label.set_label("")
        self._auth_pending = True

        def on_prompt(text: str, prompt_type):
            # LightDM is asking for a secret (password) or visible text (username).
            # We only support password-style prompts here; respond immediately.
            self._client.respond(password)

        def on_complete(authenticated: bool):
            self._auth_pending = False
            if not authenticated:
                self._show_error("Wrong password")
                return

            session_key = self._current_session["key"]
            ok = self._client.start_session(session_key)
            if not ok:
                self._show_error("Failed to start session")
                return

            # Session launched – quit the greeter process
            Application.get_default().quit()

        def on_message(text: str, msg_type):
            # Forward PAM info/error messages to the UI label
            self._error_label.set_label(text)

        self._client.authenticate(
            self._current_user,
            on_prompt=on_prompt,
            on_complete=on_complete,
            on_message=on_message,
        )


# ---------------------------------------------------------------------------
# Multi-monitor manager  (same structure as the greetd version)
# ---------------------------------------------------------------------------

class GreeterManager:
    def __init__(self, client: LightDMClient, users: list[str], sessions: list[dict]):
        self._client   = client
        self._users    = users
        self._sessions = sessions
        self._windows: dict[Gdk.Monitor, GreeterWindow] = {}

        display = Gdk.Display.get_default()
        primary = display.get_primary_monitor()

        for i in range(display.get_n_monitors()):
            mon = display.get_monitor(i)
            self._add_monitor(mon, mon == primary)

        display.connect("monitor-added",   lambda _, m: self._add_monitor(m, False))
        display.connect("monitor-removed", lambda _, m: self._remove_monitor(m))

    def _add_monitor(self, monitor: Gdk.Monitor, is_primary: bool = False):
        if monitor in self._windows:
            return
        display = Gdk.Display.get_default()
        idx = next(
            (i for i in range(display.get_n_monitors()) if display.get_monitor(i) == monitor),
            0,
        )
        window = GreeterWindow(
            self._client, self._users, self._sessions,
            monitor, idx, is_primary,
        )
        self._windows[monitor] = window

    def _remove_monitor(self, monitor: Gdk.Monitor):
        window = self._windows.pop(monitor, None)
        if window:
            window.destroy()

    @property
    def primary_window(self) -> GreeterWindow:
        display = Gdk.Display.get_default()
        primary = display.get_primary_monitor()
        return self._windows.get(primary, list(self._windows.values())[0])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    client   = LightDMClient()
    users    = get_human_users()
    sessions = get_sessions()

    manager = GreeterManager(client, users, sessions)

    app = Application("greeter", manager.primary_window)
    app.set_stylesheet_from_file(get_relative_path("./greeter.css"))

    app.run()