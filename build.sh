#!/usr/bin/env bash
# Postaví jednosouborovou binárku do dist/ — pro systém, na kterém běží.
#
# PyInstaller neumí křížovou kompilaci: binárku pro každý systém musí postavit
# ten systém. Linux se staví doma na vlastním runneru, Windows a macOS na
# půjčených strojích GitHub Actions (.github/workflows/binarky.yml).
#
# Staví se proti samostatnému CPythonu od uv, ne proti systémovému. Na Linuxu
# je slinkovaný s glibc 2.17, takže binárka jede i na letitých systémech.
# Postavená proti Pythonu z Fedory 44 by chtěla glibc 2.43 a nešla by spustit
# skoro nikde — glibc drží zpětnou kompatibilitu, ne dopřednou. Nic z hostitele
# se do ní nedostane, takže kontejner k tomu není potřeba.
set -euo pipefail

VERSION=${VERSION:-3.11}
BUILD=${BUILD:-.build}

uv python install "$VERSION"
uv venv --quiet --managed-python --python "$VERSION" "$BUILD"

# Windows dává spustitelné soubory venvu do Scripts/, zbytek světa do bin/.
python="$BUILD/bin/python"
pyinstaller="$BUILD/bin/pyinstaller"
if [ -d "$BUILD/Scripts" ]; then
    python="$BUILD/Scripts/python.exe"
    pyinstaller="$BUILD/Scripts/pyinstaller.exe"
fi

uv pip install --quiet --python "$python" -r requirements-build.txt

"$pyinstaller" --clean --noconfirm \
    --distpath dist --workpath "$BUILD/work" kostky.spec

echo
ls -lh dist/
