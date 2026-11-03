# -*- coding: utf-8 -*-

__all__ = ["MenuItem", "Profile", "Settings", "LauncherConfig"]


class MenuItem(object):

    def __init__(self, item_id, label="", icon=None, color=None, action=None,
                 args=None, kwargs=None, submenu=None):
        self.item_id    = item_id
        self.label      = label
        self.icon       = icon
        self.color = color
        self.action     = action
        self.args       = args or []
        self.kwargs     = kwargs or {}
        self.submenu    = submenu or []   # MenuItemのリスト

    def hasSubmenu(self):
        return len(self.submenu) > 0

    @classmethod
    def fromDict(cls, data):
        submenu = [cls.fromDict(child) for child in data.get("submenu", [])]
        return cls(
            item_id=data.get("id"),
            label=data.get("label", ""),
            icon=data.get("icon"),
            color=data.get("color"),
            action=data.get("action"),
            args=data.get("args"),
            kwargs=data.get("kwargs"),
            submenu=submenu
        )


class Profile(object):

    def __init__(self, profile_id, label="", icon=None, color=None, items=None):
        self.profile_id = profile_id
        self.label = label
        self.icon = icon
        self.color = color
        self.items = items or []   # MenuItemのリスト

    @classmethod
    def fromDict(cls, data):
        items = [MenuItem.fromDict(item) for item in data.get("items", [])]
        return cls(
            profile_id=data.get("id"),
            label=data.get("label", ""),
            icon=data.get("icon"),
            color=data.get("color"),
            items=items
        )


class Settings(object):

    DEFAULTS = {
        "orientation": "vertical",
        "submenu_direction": "right",
        "button_size": 48,
        "spacing": 8,
        "opacity": 1.0,
        "home_icon": None,
        "main_viewport_size": 220,
        "submenu_viewport_size": 240,
        "close_all_after_marking": False,
        "inertia_scroll_enabled": True,
        "global_scale": 1.0,     # ← 追加
        "main_scale": 1.0,        # ← 追加
        "submenu_scale": 1.0,
        "accent_color": "#FFD700",
        "base_color": "#FFFFFF",
        "breadcrumb_collapse_enabled": True,
    }

    def __init__(self, orientation="vertical", submenu_direction="right",
                 button_size=48, spacing=8, opacity=1.0, home_icon=None,
                 main_viewport_size=220, submenu_viewport_size=240,
                 close_all_after_marking=False, inertia_scroll_enabled=True,
                 global_scale=1.0, main_scale=1.0, submenu_scale=1.0, base_color="#FFFFFF",
                 accent_color="#FFD700", breadcrumb_collapse_enabled=True):   # ← 追加
        self.orientation = orientation
        self.submenu_direction = submenu_direction
        self.button_size = button_size
        self.spacing = spacing
        self.opacity = opacity
        self.home_icon = home_icon
        self.main_viewport_size = main_viewport_size
        self.submenu_viewport_size = submenu_viewport_size
        self.close_all_after_marking = close_all_after_marking
        self.inertia_scroll_enabled = inertia_scroll_enabled
        self.global_scale = global_scale     # ← 追加
        self.main_scale = main_scale           # ← 追加
        self.submenu_scale = submenu_scale       # ← 追加
        self.accent_color = accent_color
        self.base_color = base_color
        self.breadcrumb_collapse_enabled = breadcrumb_collapse_enabled

    @classmethod
    def fromDict(cls, data):
        merged = dict(cls.DEFAULTS)
        merged.update(data or {})
        return cls(**merged)


class LauncherConfig(object):

    def __init__(self, settings=None, profiles=None):
        self.settings = settings or Settings()
        self.profiles = profiles or []

    @classmethod
    def fromDict(cls, data):
        settings = Settings.fromDict(data.get("settings", {}))
        profiles = [Profile.fromDict(p) for p in data.get("profiles", [])]
        return cls(settings=settings, profiles=profiles)

    def getProfile(self, profile_id):
        for profile in self.profiles:
            if profile.profile_id == profile_id:
                return profile
        return None

    def findItem(self, profile_id, item_id):   # ← 追加
        """指定プロファイル内を再帰的に探索し、item_idに一致するMenuItemを返す。
        見つからなければNone。お気に入りの実体解決に使う"""
        profile = self.getProfile(profile_id)
        if profile is None:
            return None
        return self._find_item_recursive(profile.items, item_id)

    def _find_item_recursive(self, items, item_id):   # ← 追加
        for item in items:
            if item.item_id == item_id:
                return item
            found = self._find_item_recursive(item.submenu, item_id)
            if found is not None:
                return found
        return None