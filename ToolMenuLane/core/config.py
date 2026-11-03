# -*- coding: utf-8 -*-

import os
import json

from . import models


__all__ = ["ConfigError", "loadConfig"]


class ConfigError(Exception):
    pass


def loadConfig(path):
    if not os.path.isfile(path):
        raise ConfigError("config file not found: {0}".format(path))

    with open(path, "r") as f:
        try:
            data = json.load(f)
        except ValueError as e:
            raise ConfigError("invalid json ({0}): {1}".format(path, e))

    return models.LauncherConfig.fromDict(data)

