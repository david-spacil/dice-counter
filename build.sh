#!/usr/bin/env bash
# Postaví jednosouborovou binárku pro Linux do dist/kostky.
#
# Staví se proti samostatnému CPythonu od uv, ne proti systémovému. Ten je
# slinkovaný s glibc 2.17, takže binárka jede i na letitých systémech.
# Postavená proti Pythonu z Fedory 44 by chtěla glibc 2.43 a nešla by
# spustit skoro nikde — glibc drží zpětnou kompatibilitu, ne dopřednou.
# Nic z hostitele se do ní nedostane, takže kontejner k tomu není potřeba.
set -euo pipefail

VERSION=${VERSION:-3.11}
BUILD=${BUILD:-.build}

uv python install "$VERSION"
uv venv --quiet --managed-python --python "$VERSION" "$BUILD"
uv pip install --quiet --python "$BUILD/bin/python" -r requirements.txt pyinstaller

"$BUILD/bin/pyinstaller" --clean --noconfirm \
    --distpath dist --workpath "$BUILD/work" kostky.spec

echo
ls -lh dist/kostky
