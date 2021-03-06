from randovania.gui.dialog.logic_settings_window import LogicSettingsWindow
from randovania.interface_common.preset_editor import PresetEditor


def test_on_preset_changed(skip_qtbot, default_preset):
    # Setup
    editor = PresetEditor(default_preset)
    window = LogicSettingsWindow(None, editor)

    # Run
    window.on_preset_changed(editor.create_custom_preset_with())
