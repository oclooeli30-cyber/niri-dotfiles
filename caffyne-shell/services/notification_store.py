from gi.repository import GObject
from services.singletons import notifications

class NotificationStore(GObject.Object):
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__()
        self._notifications = []
        notifications.connect("notification-added", self._on_added)

    def _on_added(self, _, nid: int):
        notification = notifications.get_notification_from_id(nid)
        if not notification:
            return
        self._notifications.insert(0, notification)
        notification.connect("closed", self._on_closed)
        self.emit("changed")

    def _on_closed(self, notification, reason):

        if reason == "dismissed-by-user":
            if notification in self._notifications:
                self._notifications.remove(notification)
                self.emit("changed")

    def remove_all(self):
        for n in list(self._notifications):
            n.close("dismissed-by-user")
        self._notifications.clear()
        self.emit("changed")
    def remove(self, notification):
        if notification in self._notifications:
            self._notifications.remove(notification)
            self.emit("changed")
    @property
    def items(self):
        return list(self._notifications)

notification_store = NotificationStore()