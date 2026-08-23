"""Která verze počitadla to vlastně je.

Venku jsou čtyři binárky pro tři systémy a k tomu zdrojáky. Když někdo
napíše, že mu něco nefunguje, je první otázka vždycky stejná — a bez
`--version` na ni nemá jak odpovědět.
"""

import subprocess
import sys
from functools import lru_cache
from pathlib import Path

NAME = "verze.txt"
UNKNOWN = "neznámá"


def bundled() -> str:
    """Verze vypálená do binárky při stavbě.

    `build.sh` ji zapíše do souboru, `dice-counter.spec` ji přibalí. V binárce
    leží vedle šablon v dočasném adresáři, na který ukazuje `sys._MEIPASS`.
    """
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    try:
        return (root / NAME).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def described() -> str:
    """Verze podle gitu. Ze zdrojáků je to přesnější než cokoli zapsaného."""
    try:
        done = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=Path(__file__).parent, capture_output=True, text=True,
            timeout=5, check=True)
    except (OSError, subprocess.SubprocessError):
        return ""

    return done.stdout.strip()


@lru_cache(maxsize=1)
def current() -> str:
    """Verze pro výpis. Ptát se gitu má smysl jen mimo binárku."""
    if getattr(sys, "frozen", False):
        return bundled() or UNKNOWN

    return described() or bundled() or UNKNOWN
