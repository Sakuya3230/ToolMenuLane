# -*- coding: utf-8 -*-

import os
import json
import tempfile

try:
    import getpass
    _USERNAME = getpass.getuser()
except Exception:
    _USERNAME = "unknown"


__all__ = ["loadState", "saveState", "statePath"]

STATE_FILENAME = "ToolMenuLane_settings.json"


def statePath():
    return os.path.join(tempfile.gettempdir(), STATE_FILENAME)


def loadState():
    path = statePath()
    if not os.path.isfile(path):
        return {}

    try:
        with open(path, "r") as f:
            return json.load(f)
    except (ValueError, IOError):
        # 壊れたファイル・読み込み権限なし等は「保存された状態が無い」のと同じ扱いにする
        return {}


def saveState(data):
    path = statePath()
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except IOError:
        pass   # 保存失敗しても起動不能にはしたくないため、ここでは黙って諦める