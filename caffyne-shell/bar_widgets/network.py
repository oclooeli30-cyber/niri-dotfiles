from .base import ProgressButton
from services.singletons import network
from icons import NetworkIcon
 
class NetworkButton(ProgressButton):
    def __init__(self, monitor_id, vertical, variant=None, **kwargs):
        super().__init__(
            icon=lambda size: NetworkIcon(size),
            label="",
            variant=variant or "icon+label",
            **kwargs,
        )
        network.connect("device-ready", self._on_device_ready)
        self._on_device_ready()
 
    def _on_device_ready(self, *_):
        if network.wifi_device:
            network.wifi_device.connect("changed", self._update)
        if network.ethernet_device:
            network.ethernet_device.connect("changed", self._update)
        self._update()
 
    def _update(self, *_):
        wifi = network.wifi_device
        eth = network.ethernet_device
        eth_active = eth and eth.internet == "activated"
        wifi_active = wifi and wifi.internet == "activated"
        show_label = wifi_active and not eth_active
 
        if show_label and wifi:
            value = max(0, wifi.strength)
            self._update_label(f"{value}%")
            self._update_value(value)
        else:
            self._update_label("")
            self._update_value(0)