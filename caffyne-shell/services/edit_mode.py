from fabric.core.service import Service, Property

class EditMode(Service):
    """
    Global edit mode service for managing edit state across the shell.
    Used by bars, desktop widgets, and other draggable components.
    """

    @Property(bool, "readable", default_value=False)
    def edit_mode(self) -> bool:
        return self._property_helper_edit_mode

    def __init__(self, **kwargs):
        self._property_helper_edit_mode = False
        super().__init__(**kwargs)

    def toggle(self) -> None:
        self._property_helper_edit_mode = not self._property_helper_edit_mode
        self.notify("edit-mode")

    def enable(self) -> None:
        if not self._property_helper_edit_mode:
            self._property_helper_edit_mode = True
            self.notify("edit-mode")

    def disable(self) -> None:
        if self._property_helper_edit_mode:
            self._property_helper_edit_mode = False
            self.notify("edit-mode")