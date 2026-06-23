from ..base.workspace import WMWorkspace


class NiriWorkspace(WMWorkspace):

    def __init__(self, service, **kwargs):
        self.__service = service
        super().__init__(**kwargs)

    def switch_to(self) -> None:
        self.__service.send_command(
            {"Action": {"FocusWorkspace": {"reference": {"Id": self.id}}}}
        )
