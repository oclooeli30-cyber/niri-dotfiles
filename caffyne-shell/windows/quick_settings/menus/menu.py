from fabric.widgets.box import Box
from fabric.widgets.button import Button
from typing import Callable
from snippets import AppletPage
from snippets import RotatingIcon
from snippets import Switch

class QSAppletPage(AppletPage):
    def __init__(
        self,
        title: str,
        child,
        stack=None,
        switch: Switch | None = None,
        button_icon_name: str | None = None,
        button_action: Callable | None = None,
        **kwargs,
    ):
        header_children = []

        if switch is not None:
            self.switch = switch
            header_children.append(self.switch)

        if button_icon_name:
            header_children.append(
                Button(
                    style_classes=["applet-misc-button"],
                    child=RotatingIcon(icon_name=button_icon_name),
                    on_clicked=button_action,
                )
            )

        super().__init__(
            title=title,
            child=child,
            stack=stack,
            first=stack is None,
            header_right_children=Box(
                h_expand=False,
                spacing=12,
                children=header_children,
            ) if header_children else [],
            **kwargs,
        )