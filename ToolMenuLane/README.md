# パッケージ構成 ──────────────────────────────────────────────────────────────────────

ToolMenuLane/
├── __init__.py          # `from . import api` + 薄いmain()ラッパー
├── api.py                 # reloader.reload_all()を呼んでからshow_window()を呼ぶだけ
├── reloader.py             # MODULES管理 + reload_all()専用
├── core/
│   ├── __init__.py
│   ├── config.py           # (未実装)
│   ├── models.py           # (未実装)
│   ├── state.py             # (未実装)
│   └── registry.py          # 実装方針確定済み（module.path:function 解決）
├── ui/
│   ├── __init__.py
│   ├── main_window.py        # ← 今回ここから着手（ToolMenuLaneWindow + show_window）
│   └── widgets/
│       ├── __init__.py
│       ├── donut_button.py    # (未実装)
│       ├── main_menu_area.py  # (未実装)
│       ├── indicator.py       # (未実装)
│       ├── sub_menu_row.py    # (未実装)
│       ├── sub_menu_panel.py  # (未実装)
│       └── radial_menu.py     # (未実装)
├── controller/
│   ├── __init__.py
│   ├── launcher_controller.py  # (未実装)
│   └── profile_controller.py   # (未実装)
└── resources/
    └── default_config.json      # (未実装)


ドラッグ中は展開を自動化　
リリースで起動して閉じる
サブメニューの親に戻れるようにしたい。

親を閉じると戻りずらい