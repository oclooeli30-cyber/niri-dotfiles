from fabric.core.service import Service, Signal, Property
from .window import WMWindow
from .workspace import WMWorkspace
from .keyboard import WMKeyboardLayouts


class WMService(Service):
    """
    Abstract base class for window manager services.

    Provides a unified interface for widgets to consume regardless of
    the underlying WM. Supports: Niri, Hyprland (and extensible to others).

    Signals:
        ready: emitted once the service has finished its initial sync.

    Properties:
        is_available:    whether the WM socket/env is detectable.
        windows:         list of all open WMWindow objects.
        active_window:   the currently focused WMWindow (or empty window).
        workspaces:      list of all WMWorkspace objects.
        active_output:   name of the currently focused monitor/output.
        keyboard_layouts: WMKeyboardLayouts instance, or None if unsupported.
    """

    @Signal
    def ready(self): ...

    @Property(bool, "readable", default_value=False)
    def is_available(self) -> bool:
        return False

    @Property(object, "readable", default_value=None)
    def windows(self) -> list[WMWindow]:
        return []

    @Property(object, "readable", default_value=None)
    def active_window(self) -> WMWindow:
        return None

    @Property(object, "readable", default_value=None)
    def workspaces(self) -> list[WMWorkspace]:
        return []

    @Property(str, "readable", default_value="")
    def active_output(self) -> str:
        return ""

    @Property(object, "readable", default_value=None)
    def keyboard_layouts(self) -> WMKeyboardLayouts | None:
        return None

    def switch_to_workspace(self, idx: int) -> None:
        """Switch to workspace by index. Override in subclass."""
        raise NotImplementedError

    def switch_to_workspace_by_id(self, workspace_id: int) -> None:
        """Switch to workspace by ID. Override in subclass."""
        raise NotImplementedError

    def get_workspace_by_id(self, workspace_id: int) -> WMWorkspace | None:
        """Look up a workspace by its ID. Override in subclass."""
        raise NotImplementedError
