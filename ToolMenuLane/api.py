# -*- coding: utf-8 -*-

from . import reloader
from .ui import window

import importlib
importlib.reload(reloader)

__all__ = [
    "show_window", 
    "reload_modules"
]

def show_window():
    reloader.reload_modules()
    window.show_window()

def reload_modules():
    reloader.reload_modules()