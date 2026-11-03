# -*- coding: utf-8 -*-

__all__ = ["ping", "echo"]


def ping():
    print(u"[ToolMenuLane] ping action executed")


def echo(message="hello"):
    print(u"[ToolMenuLane] echo: {0}".format(message))