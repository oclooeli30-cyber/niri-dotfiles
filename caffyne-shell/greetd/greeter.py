import gi, json, socket, os, pwd
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib
from fabric.widgets.wayland import WaylandWindow as Window
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
from snippets import Icon
import datetime
from utils.helpers import load_blurred_pixbuf, load_scaled_pixbuf
import threading

class GreetdClient:
    """Thin wrapper around the greetd JSON IPC socket.
    One instance is shared across all monitor windows."""

    def __init__(self):
        sock_path = os.environ.get("GREETD_SOCK")
        if not sock_path:
            raise RuntimeError("GREETD_SOCK is not set – are we running inside greetd?")
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(sock_path)
        self._session_active = False

    def _send(self, payload: dict) -> dict:
        data = json.dumps(payload).encode()
        self._sock.sendall(len(data).to_bytes(4, "little") + data)
        raw_len = self._sock.recv(4)
        length = int.from_bytes(raw_len, "little")
        return json.loads(self._sock.recv(length))

    def create_session(self, username: str) -> dict:
        resp = self._send({"type": "create_session", "username": username})
        if resp.get("type") != "error":
            self._session_active = True
        return resp

    def post_auth_message_response(self, response: str | None) -> dict:
        return self._send({"type": "post_auth_message_response", "response": response})

    def start_session(self, cmd: list[str]) -> dict:
        resp = self._send({"type": "start_session", "cmd": cmd})
        if resp.get("type") != "error":
            self._session_active = False
        return resp

    def cancel_session(self) -> dict:
        resp = self._send({"type": "cancel_session"})
        self._session_active = False
        return resp

    def close(self):
        if self._session_active:
            self.cancel_session()
        self._sock.close()

def get_human_users() -> list[str]:
    no_login = {"/usr/sbin/nologin", "/sbin/nologin", "/bin/false", "/usr/bin/false"}
    return sorted(
        p.pw_name for p in pwd.getpwall()
        if p.pw_uid >= 1000 and p.pw_shell not in no_login
    )

def get_wayland_sessions() -> list[dict]:
    sessions_dir = "/usr/share/wayland-sessions"
    sessions = []
    try:
        for fname in sorted(os.listdir(sessions_dir)):
            if not fname.endswith(".desktop"):
                continue
            name, exec_cmd = fname.replace(".desktop", ""), None
            with open(os.path.join(sessions_dir, fname)) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("Name="):
                        name = line[5:]
                    elif line.startswith("Exec="):
                        exec_cmd = line[5:]
            if exec_cmd:
                sessions.append({"name": name, "cmd": exec_cmd.split()})
    except FileNotFoundError:
        pass
    return sessions or [{"name": "Bash (fallback)", "cmd": ["/bin/bash"]}]

class DropdownPicker(Button):
    def __init__(self, items: list[str], on_change, **kwargs):
        self._items = items
        self._on_change = on_change
        self._selected = 0

        self._menu = Gtk.Menu()
        for i, item in enumerate(items):
            menu_item = Gtk.MenuItem(label=item)
            menu_item.connect("activate", lambda _, idx=i: self._select(idx))
            menu_item.show()
            self._menu.append(menu_item)

        super().__init__(
            label=items[0] if items else "",
            on_pressed=self._on_pressed,
            **kwargs
        )

    def _on_pressed(self, button):
        self._menu.popup_at_pointer(None)

    def _select(self, idx: int):
        self._selected = idx
        self.set_label(self._items[idx])
        self._on_change(idx)

    @property
    def selected_index(self) -> int:
        return self._selected

class GreeterWindow(Window):
    def __init__(self, client: GreetdClient, users: list[str], sessions: list[dict], monitor: Gdk.Monitor,  monitor_idx: int):

        self._client = client
        self._users = users
        self._sessions = sessions
        self._current_user = users[0] if users else ""
        self._current_session = sessions[0]

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

        self.geo = monitor.get_geometry()
        
        self._bg_image=Image(pixbuf=load_scaled_pixbuf(
            path="/usr/share/backgrounds/wallpaper",
            width=self.geo.width,
            height=self.geo.height,
        ))

        super().__init__(
            anchor="top bottom left right",
            layer="top",
            visible=True,
            all_visible=True,
            keyboard_mode="on-demand",
            monitor=monitor_idx,
            child=Overlay(
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
            ),
        )

        GLib.timeout_add(1000, self._update_time)
        self._update_time()
        self._entry_field.grab_focus()
        threading.Thread(target=self._load_wallpaper, daemon=True).start()

    def _load_wallpaper(self):
        pixbuf = load_blurred_pixbuf(
            path="/usr/share/backgrounds/wallpaper",
            width=self.geo.width,
            height=self.geo.height,
        )
        GLib.idle_add(self._bg_image.set_from_pixbuf, pixbuf)
        return False 

    def _update_time(self):
        now = datetime.datetime.now()
        self.clock_label.set_label(now.strftime("%H\n%M"))
        self.clock_progress.value = int(now.strftime("%S"))
        return True

    def _on_user_change(self, idx: int):
        self._current_user = self._users[idx]
        self._entry_field.set_text("")
        self._error_label.set_label("")

    def _on_session_change(self, idx: int):
        self._current_session = self._sessions[idx]

    def _show_error(self, msg: str):
        self._error_label.set_label(msg)
        self._entry_field.set_text("")

    def _on_activate(self, entry: Entry, *_):

        if self._client._session_active:
            return

        password = (entry.get_text() or "").strip()
        self._error_label.set_label("")

        resp = self._client.create_session(self._current_user)
        if resp.get("type") == "error":
            self._show_error(resp.get("description", "Session error"))
            return

        if resp.get("type") == "auth_message":
            resp = self._client.post_auth_message_response(password)

        if resp.get("type") == "error":
            self._client.cancel_session()
            self._show_error("Wrong password")
            return

        if resp.get("type") == "success":
            resp = self._client.start_session(self._current_session["cmd"])
            if resp.get("type") == "error":
                self._show_error(resp.get("description", "Failed to start session"))
                return
            Application.get_default().quit()
            return

        self._show_error("Unexpected response from greetd")

class GreeterManager:
    def __init__(self, client: GreetdClient, users: list[str], sessions: list[dict]):
        self._client = client
        self._users = users
        self._sessions = sessions
        self._windows: dict[Gdk.Monitor, GreeterWindow] = {}

        display = Gdk.Display.get_default()
        for i in range(display.get_n_monitors()):
            self._add_monitor(display.get_monitor(i))

        display.connect("monitor-added", lambda _, mon: self._add_monitor(mon))
        display.connect("monitor-removed", lambda _, mon: self._remove_monitor(mon))

    def _add_monitor(self, monitor: Gdk.Monitor):
        if monitor in self._windows:
            return
        display = Gdk.Display.get_default()
        for i in range(display.get_n_monitors()):
            if display.get_monitor(i) == monitor:
                idx = i
                break
        else:
            idx = 0
        window = GreeterWindow(self._client, self._users, self._sessions, monitor, idx)
        self._windows[monitor] = window

    def _remove_monitor(self, monitor: Gdk.Monitor):
        window = self._windows.pop(monitor, None)
        if window:
            window.destroy()

    @property
    def primary_window(self) -> GreeterWindow:
        return list(self._windows.values())[0]

if __name__ == "__main__":
    client = GreetdClient()
    users = get_human_users()
    sessions = get_wayland_sessions()

    manager = GreeterManager(client, users, sessions)

    app = Application("greeter", manager.primary_window)
    app.set_stylesheet_from_file(get_relative_path("./style/style.css"))

    try:
        app.run()
    finally:
        client.close()
