#!/usr/bin/env bash
# Postaví jednosouborovou binárku pro Linux do dist/kostky.
#
# Staví se v kontejneru s glibc 2.28 (AlmaLinux 8), ne na hostiteli. Binárka
# slinkovaná proti glibc z Fedory 44 by nešla spustit nikde se starším
# systémem — glibc drží zpětnou kompatibilitu, ne dopřednou. Postavené na
# staré glibc poběží i na nové.
set -euo pipefail

IMAGE=${IMAGE:-docker.io/library/almalinux:8}
PYTHON=${PYTHON:-python3.11}
ENGINE=${ENGINE:-$(command -v podman || command -v docker)}

# Rootless podman mapuje roota v kontejneru na tebe, docker ne — tam by
# dist/ zůstalo cizí.
FIXUP=":"
[[ "$ENGINE" == *docker ]] && FIXUP="chown -R $(id -u):$(id -g) dist"

"$ENGINE" run --rm -v "$PWD:/src:z" -w /src "$IMAGE" bash -euc "
    dnf install -y -q python3.11 binutils
    $PYTHON -m venv /tmp/build
    /tmp/build/bin/pip install --quiet --upgrade pip
    /tmp/build/bin/pip install --quiet flask qrcode pyinstaller
    /tmp/build/bin/pyinstaller --clean --noconfirm \
        --distpath dist --workpath /tmp/work kostky.spec
    $FIXUP
"

echo
ls -lh dist/kostky
