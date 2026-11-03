# -*- coding: utf-8 -*-

import sys

try:
    from importlib import import_module, reload as reload_module
except ImportError:
    import_module = lambda name: __import__(name)
    reload_module = reload 


__all__ = ["reload_modules"]

MODULES = [
    "ToolMenuLane.core.models",
    "ToolMenuLane.core.config",
    "ToolMenuLane.core.state",
    "ToolMenuLane.core.registry",
    "ToolMenuLane.core.debug_actions",
    "ToolMenuLane.controller.settings_manager",
    "ToolMenuLane.controller.favorites_manager",
    "ToolMenuLane.ui.theme",
    "ToolMenuLane.ui.anim.stagger",
    "ToolMenuLane.ui.widgets.edge_fade_effect",
    "ToolMenuLane.ui.widgets.scrollable_area",
    "ToolMenuLane.ui.widgets.donut_button",
    "ToolMenuLane.ui.widgets.home_button",
    "ToolMenuLane.ui.widgets.radial_menu",
    "ToolMenuLane.ui.widgets.favorites_radial_menu",
    "ToolMenuLane.ui.widgets.pointer_overlay",
    "ToolMenuLane.ui.widgets.sub_menu_row",
    "ToolMenuLane.ui.widgets.main_menu_area",
    "ToolMenuLane.ui.widgets.sub_menu_panel",
    "ToolMenuLane.ui.widgets.indicator",
    "ToolMenuLane.ui.widgets.settings_dialog",
    "ToolMenuLane.ui.widgets.menu_config_editor",
    "ToolMenuLane.controller.launcher_controller",
    "ToolMenuLane.ui.window",
    "ToolMenuLane.api",
]


def reload_modules():
    for name in MODULES:
        if name in sys.modules:
            reload_module(sys.modules[name])
        else:
            import_module(name)