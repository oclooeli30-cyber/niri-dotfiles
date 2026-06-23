from fabric.widgets.label import Label
from services.singletons import network
from .button import QSButton
from icons import NetworkIcon

class WifiButton(QSButton):
    def __init__(self, stack, **kwargs):
        self.label = Label(label="Wifi")
        super().__init__(
            icon=NetworkIcon(size=16),
            label=self.label,
            on_activate=lambda _: network.wifi_device and setattr(network.wifi_device, "enabled", True),
            on_deactivate=lambda _: network.wifi_device and setattr(network.wifi_device, "enabled", False),
            menu_name="wifi",
            stack=stack,
            **kwargs,
        )
        network.connect("device-ready", self._on_device_ready)
        self._on_device_ready()
    def _on_device_ready(self, *_):
        if network.ethernet_device:
            network.ethernet_device.connect(
                "notify::internet",
                lambda obj, _: self.label.set_label(
                    "Ethernet" if obj.internet == "activated" else "Wifi"
                ),
            )
            self.label.set_label(
                "Ethernet" if network.ethernet_device.internet == "activated" else "Wifi"
            )
        if network.wifi_device:
            network.wifi_device.connect(
                "notify::enabled",
                lambda obj, _: setattr(self, "active", obj.enabled),
            )
            setattr(self, "active", network.wifi_device.enabled)