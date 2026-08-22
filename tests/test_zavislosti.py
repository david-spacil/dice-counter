"""Závislosti jsou zamčené a všechna místa se shodnou.

Verze se píšou na dvou místech: v `requirements.txt` pro stavbu binárky
a v hlavičce PEP 723 pro `uv run web.py`. Ta dvě místa se dřív nebo později
rozejdou — leda že by to někdo hlídal. Proto tenhle soubor.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent

# Skript a to, co si podle hlavičky nese s sebou.
SCRIPTS = {"web.py": {"flask", "qrcode", "waitress"},
           "dice.py": {"tabulate"}}


def pins(name: str) -> dict[str, str]:
    """Zamčené verze z compilovaného requirements souboru."""
    text = (ROOT / name).read_text(encoding="utf-8")
    return {m.group(1).lower(): m.group(2)
            for m in re.finditer(r"^([A-Za-z0-9_.\-]+)==(\S+)", text, re.M)}


def header(script: str) -> dict[str, str]:
    """Závislosti z hlavičky PEP 723 na začátku skriptu."""
    text = (ROOT / script).read_text(encoding="utf-8")
    line = re.search(r"^# dependencies = \[(.*)\]$", text, re.M)
    assert line, f"{script} nemá hlavičku PEP 723"

    return {m.group(1).lower(): m.group(2)
            for m in re.finditer(r'"([A-Za-z0-9_.\-]+)==(\S+?)"', line.group(1))}


@pytest.mark.parametrize("name", ["requirements.txt", "requirements-dev.txt",
                                  "requirements-build.txt"])
def test_zavislosti_jsou_zamcene(name):
    """Bez zamčených verzí se binárka z března liší od binárky z dubna."""
    lines = [line.strip() for line in (ROOT / name).read_text().splitlines()]
    volne = [line for line in lines
             if line and not line.startswith("#") and "==" not in line]

    assert not volne, f"{name} má nezamčené závislosti: {volne}"


@pytest.mark.parametrize("script", sorted(SCRIPTS))
def test_hlavicka_sedi_s_requirements(script):
    """`uv run web.py` musí dostat totéž, co se zabalí do binárky."""
    zamcene = pins("requirements.txt")
    v_hlavicce = header(script)

    assert set(v_hlavicce) == SCRIPTS[script]

    for balicek, verze in v_hlavicce.items():
        assert balicek in zamcene, f"{balicek} chybí v requirements.txt"
        assert verze == zamcene[balicek], (
            f"{script}: {balicek}=={verze}, ale zamčeno je "
            f"{zamcene[balicek]} — přepiš hlavičku")
