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

PYTHON_VERSION=${PYTHON_VERSION:-3.11}
BUILD=${BUILD:-.build}

# Verze, kterou binárka ohlásí přes --version. V CI ji na tagu vnutíme
# proměnnou, protože tam je repozitář naklonovaný na jeden commit a git
# describe nemá o co se opřít.
VERSION=${VERSION:-$(git describe --tags --always --dirty 2>/dev/null || echo neznámá)}
printf '%s\n' "$VERSION" > verze.txt
echo "Verze: $VERSION"

uv python install "$PYTHON_VERSION"
# --clear, protože runner si pracovní adresář mezi běhy drží a uv nad
# existujícím prostředím jinak skončí chybou. Stavíme načisto.
uv venv --quiet --clear --managed-python --python "$PYTHON_VERSION" "$BUILD"

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
