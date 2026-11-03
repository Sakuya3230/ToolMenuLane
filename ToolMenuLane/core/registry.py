# -*- coding: utf-8 -*-

try:
    from importlib import import_module
except ImportError:
    import sys

    def import_module(name):
        __import__(name)
        return sys.modules[name]


__all__ = ["ActionResolveError", "resolve_action", "call_action", "clear_cache"]

_cache = {}

# コード実行モードで、あらかじめ使えるようにしておく名前空間。
# よく使うMayaモジュールをここに用意しておくことで、JSON側で毎回importを
# 書かなくても済むようにする(書きたければ書いても問題ない)
_EXEC_GLOBALS = {}


def _build_exec_globals():
    if _EXEC_GLOBALS:
        return _EXEC_GLOBALS

    try:
        import maya.cmds as cmds
        _EXEC_GLOBALS["cmds"] = cmds
    except ImportError:
        pass

    try:
        import maya.mel as mel
        _EXEC_GLOBALS["mel"] = mel
    except ImportError:
        pass

    try:
        import maya.api.OpenMaya as om2
        _EXEC_GLOBALS["om2"] = om2
    except ImportError:
        pass

    return _EXEC_GLOBALS


class ActionResolveError(Exception):
    pass


def resolve_action(action_id):
    if action_id in _cache:
        return _cache[action_id]

    if not action_id:
        raise ActionResolveError(u"empty action id")

    if ":" not in action_id:
        # コード実行モード。resolve時点では構文チェックのみ行い、
        # 実際の実行はcall_action側でその都度行う(引数を毎回渡せるようにするため)
        try:
            compile(action_id, "<ToolMenuLane action>", "exec")
        except SyntaxError as e:
            raise ActionResolveError(u"invalid python code: {0}".format(e))

        _cache[action_id] = ("code", action_id)
        return _cache[action_id]

    module_path, func_name = action_id.split(":", 1)

    try:
        module = import_module(module_path)
    except ImportError as e:
        raise ActionResolveError(u"cannot import '{0}': {1}".format(module_path, e))

    target = module
    for attr in func_name.split("."):
        try:
            target = getattr(target, attr)
        except AttributeError:
            raise ActionResolveError(
                u"'{0}' has no attribute '{1}'".format(module_path, func_name)
            )

    if not callable(target):
        raise ActionResolveError(u"'{0}:{1}' is not callable".format(module_path, func_name))

    _cache[action_id] = ("callable", target)
    return _cache[action_id]


def call_action(action_id, *args, **kwargs):
    kind, target = resolve_action(action_id)

    if kind == "callable":
        return target(*args, **kwargs)

    # コード実行モード。argsは"arg0", "arg1"...、kwargsはそのままの名前で
    # コード内から参照できるようにしてから実行する
    exec_globals = dict(_build_exec_globals())
    exec_locals = dict(kwargs)
    for i, value in enumerate(args):
        exec_locals["arg{0}".format(i)] = value

    exec(target, exec_globals, exec_locals)


def clear_cache():
    _cache.clear()