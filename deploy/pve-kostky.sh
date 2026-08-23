#!/usr/bin/env bash
# Skript se přejmenoval na deploy/pve-dice-counter.sh.
#
# Tenhle soubor tu zůstává schválně. Příkaz `update` v už založených
# kontejnerech si instalátor stahuje z téhle adresy — kdyby zmizela,
# aktualizace by u nich přestala fungovat dřív, než se stihnou přemigrovat.
# Až se tak stane, zmizí i tenhle soubor.
#
# Předává se všechno beze změny, včetně argumentů a proměnných prostředí.
# Na stdout nesmí přibýt ani řádek navíc: starý `update` si sem chodí pro
# `instalator` a výstup rovnou kontroluje přes `bash -n`.
set -euo pipefail

GITEA="${GITEA:-https://gitea.spacilovi.eu}"
REPO="${REPO:-david-spacil/dice-counter}"

NOVY=$(mktemp)
trap 'rm -f "$NOVY"' EXIT

curl -fsSL "$GITEA/$REPO/raw/branch/main/deploy/pve-dice-counter.sh" -o "$NOVY" \
    || { echo "Skript se přesunul do deploy/pve-dice-counter.sh, ale nejde stáhnout." >&2; exit 1; }

bash "$NOVY" "$@"
