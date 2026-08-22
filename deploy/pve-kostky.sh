#!/usr/bin/env bash
# Založí na Proxmoxu LXC kontejner s počitadlem kostek.
#
# Pouští se v terminálu uzlu Proxmoxu jako root:
#
#     bash pve-kostky.sh                # nový kontejner
#     bash pve-kostky.sh update 123     # aktualizace toho stávajícího
#
# Podoba je odkoukaná od community-scripts.org, ale nic z jejich frameworku
# se tu nestahuje — jejich build.func si instalační skript hledá natvrdo ve
# vlastním repozitáři, takže mimo něj nefunguje.
#
# Počítá se s domácí sítí. Appka nemá přihlašování a tenhle skript ji nijak
# nezabezpečuje; do internetu ji nepouštěj.
set -euo pipefail

APP="Kostky"
REPO_URL="https://gitea.spacilovi.eu/david-spacil/dice-counter"

# Výchozí hodnoty. Všechny se dají přebít proměnnou prostředí, třeba:
#     MEMORY=1024 STORAGE=local-zfs bash pve-kostky.sh
CT_HOSTNAME="${CT_HOSTNAME:-kostky}"
CORES="${CORES:-1}"
MEMORY="${MEMORY:-512}"
DISK="${DISK:-4}"
STORAGE="${STORAGE:-local-lvm}"
TEMPLATE_STORAGE="${TEMPLATE_STORAGE:-local}"
BRIDGE="${BRIDGE:-vmbr0}"
PORT="${PORT:-8000}"
UNPRIVILEGED="${UNPRIVILEGED:-1}"
OSVERSION="${OSVERSION:-13}"

INSTALLER="$(dirname "$(readlink -f "$0")")/lxc-install.sh"

# --- výpisy ------------------------------------------------------------------

msg() { echo -e "\e[1;34m  →\e[0m $*"; }
ok()  { echo -e "\e[1;32m  ✓\e[0m $*"; }
die() { echo -e "\e[1;31m  ✗\e[0m $*" >&2; exit 1; }

header() {
    echo
    echo -e "\e[1;36m  $APP\e[0m — počitadlo kostek do LXC"
    echo -e "  \e[2m$REPO_URL\e[0m"
    echo
}

# --- kontroly, než se něco založí -------------------------------------------

command -v pct >/dev/null || die "Tohle patří na uzel Proxmoxu — pct tu není."
[ "$(id -u)" -eq 0 ] || die "Spusť to jako root."
[ -f "$INSTALLER" ] || die "Vedle skriptu chybí lxc-install.sh."

# --- instalace do kontejneru -------------------------------------------------

install_into() {
    local ctid="$1"

    msg "Posílám instalátor do kontejneru $ctid"
    pct push "$ctid" "$INSTALLER" /root/lxc-install.sh --perms 0755

    pct exec "$ctid" -- env PORT="$PORT" bash /root/lxc-install.sh
}

address_of() {
    local ctid="$1"
    pct exec "$ctid" -- hostname -I 2>/dev/null | awk '{print $1}'
}

hotovo() {
    local ctid="$1" ip jmeno
    ip=$(address_of "$ctid")
    jmeno=$(pct config "$ctid" | awk -F': ' '/^hostname:/ {print $2}')

    echo
    ok "Hotovo. Kontejner $ctid ($jmeno) běží."
    echo
    echo -e "  Zápisník na notebook:  \e[1;32mhttp://${ip}:${PORT}/board\e[0m"
    echo -e "  Zadávání z telefonu:   \e[1;32mhttp://${ip}:${PORT}/\e[0m"
    echo
    echo -e "  \e[2mDatabáze:  /var/lib/kostky/dice.db (uvnitř kontejneru)"
    echo -e "  Log:       pct exec $ctid -- journalctl -u kostky -f"
    echo -e "  Konzole:   pct enter $ctid\e[0m"
    echo
}

# --- aktualizace -------------------------------------------------------------

if [ "${1:-}" = "update" ]; then
    ctid="${2:-}"
    [ -n "$ctid" ] || die "Řekni který: bash pve-kostky.sh update <ctid>"
    pct status "$ctid" >/dev/null 2>&1 || die "Kontejner $ctid neexistuje."

    header
    [ "$(pct status "$ctid")" = "status: running" ] || {
        msg "Startuji kontejner"
        pct start "$ctid"
        sleep 5
    }

    install_into "$ctid"
    hotovo "$ctid"
    exit 0
fi

# --- nový kontejner ----------------------------------------------------------

header

CTID="${CTID:-$(pvesh get /cluster/nextid)}"
msg "Kontejner dostane číslo $CTID"

msg "Hledám šablonu Debianu $OSVERSION"
pveam update >/dev/null 2>&1 || true
TEMPLATE=$(pveam available --section system \
    | awk '{print $2}' | grep "^debian-${OSVERSION}-standard" | sort -V | tail -1)
[ -n "$TEMPLATE" ] || die "Šablona pro Debian $OSVERSION není k dispozici."

if ! pveam list "$TEMPLATE_STORAGE" 2>/dev/null | grep -q "$TEMPLATE"; then
    msg "Stahuji $TEMPLATE"
    pveam download "$TEMPLATE_STORAGE" "$TEMPLATE" >/dev/null
fi
ok "Šablona $TEMPLATE"

msg "Zakládám kontejner"
pct create "$CTID" "$TEMPLATE_STORAGE:vztmpl/$TEMPLATE" \
    --hostname "$CT_HOSTNAME" \
    --cores "$CORES" \
    --memory "$MEMORY" \
    --swap 256 \
    --rootfs "$STORAGE:$DISK" \
    --net0 "name=eth0,bridge=$BRIDGE,ip=dhcp" \
    --unprivileged "$UNPRIVILEGED" \
    --ostype debian \
    --onboot 1 \
    --description "$APP — $REPO_URL" >/dev/null
ok "Kontejner $CTID založen"

msg "Startuji"
pct start "$CTID"

msg "Čekám na síť"
for _ in $(seq 60); do
    [ -n "$(address_of "$CTID")" ] \
        && pct exec "$CTID" -- getent hosts deb.debian.org >/dev/null 2>&1 \
        && break
    sleep 2
done
[ -n "$(address_of "$CTID")" ] || die "Kontejner nedostal adresu. Sedí bridge $BRIDGE?"
ok "Adresa $(address_of "$CTID")"

install_into "$CTID"
hotovo "$CTID"
