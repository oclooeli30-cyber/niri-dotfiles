from fabric.widgets.box import Box

class DockSeparator(Box):
    """A simple vertical separator between workspace groups in the dock."""

    def __init__(self, **kwargs):
        super().__init__(
            style_classes=["dock-separator"],
            **kwargs,
        )
