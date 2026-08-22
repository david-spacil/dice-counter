# -*- mode: python ; coding: utf-8 -*-
"""Jedna binárka se vším: Python, Flask, šablony i styly.

Staví se přes `./build.sh`, ne ručně — ta se stará o to, aby výsledek jel
i na starších systémech, než je ten tvůj.
"""

import sys

analysis = Analysis(
    ["web.py"],
    pathex=["."],
    datas=[("templates", "templates"), ("static", "static")],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    name="kostky",
    console=True,
    # Ořezání symbolů šetří pár megabajtů, ale jen na Linuxu. Na macOS by
    # rozbilo podpis, který si PyInstaller sám přidává a bez kterého se
    # binárka na Apple Silicon vůbec nespustí; na Windows nedělá nic.
    strip=sys.platform == "linux",
    upx=False,
)
