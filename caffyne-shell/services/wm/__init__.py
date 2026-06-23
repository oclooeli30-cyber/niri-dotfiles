"""
services/wm — unified window manager abstraction for Fabric shells.

Supports: Niri, Hyprland.

Usage:
    from services.wm import get_wm_service, WMService

    wm = get_wm_service()          # auto-detects running WM
    wm.connect("notify::windows", ...)
    wm.connect("notify::workspaces", ...)

All window/workspace objects conform to the WMWindow / WMWorkspace base
interfaces regardless of the underlying compositor.
"""

import os
from .base import WMService, WMWindow, WMWorkspace, WMKeyboardLayouts

_wm_instance: WMService | None = None


def get_wm_service() -> WMService:
    """
    Return the singleton WMService for the currently running compositor.
    Auto-detects based on environment variables. Raises RuntimeError if
    no supported WM is detected.
    """
    global _wm_instance
    if _wm_instance is not None:
        return _wm_instance

    if os.getenv("NIRI_SOCKET"):
        from .niri.service import Niri
        _wm_instance = Niri()
        # _wm_instance = None
    elif os.getenv("HYPRLAND_INSTANCE_SIGNATURE"):
        from .hyprland.service import Hyprland
        _wm_instance = Hyprland()

    elif os.getenv("MANGO_INSTANCE_SIGNATURE"):
        from .mango.service import Mango
        _wm_instance = Mango()
        
    else:
        raise RuntimeError(
            "No supported window manager detected. "
            "Expected NIRI_SOCKET or HYPRLAND_INSTANCE_SIGNATURE to be set."
        )

    return _wm_instance


__all__ = [
    "get_wm_service",
    "WMService",
    "WMWindow",
    "WMWorkspace",
    "WMKeyboardLayouts",
]
