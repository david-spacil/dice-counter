# -*- mode: python ; coding: utf-8 -*-
"""Jedna binárka se vším: Python, Flask, šablony i styly.

Staví se přes `./build.sh`, ne ručně — ta se stará o to, aby výsledek jel
i na starších systémech, než je ten tvůj.
"""

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
    strip=True,
    upx=False,
)
