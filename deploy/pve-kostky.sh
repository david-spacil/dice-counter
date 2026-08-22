#!/usr/bin/env bash
# Založí na Proxmoxu LXC kontejner s počitadlem kostek.
#
# Pouští se v terminálu uzlu Proxmoxu jako root, jedním příkazem:
#
#   bash -c "$(curl -fsSL https://gitea.spacilovi.eu/david-spacil/dice-counter/raw/branch/main/deploy/pve-kostky.sh)"
#
# Aktualizace stávajícího kontejneru na novější vydání:
#
#   CTID=123 MODE=update bash -c "$(curl -fsSL .../pve-kostky.sh)"
#
# Ze staženého souboru jde i obojí postaru: `bash pve-kostky.sh` a
# `bash pve-kostky.sh update 123`.
#
# Podoba je odkoukaná od community-scripts.org, ale nic z jejich frameworku
# se tu nestahuje — jejich build.func si instalační skript hledá natvrdo ve
# vlastním repozitáři, takže mimo něj nefunguje.
#
# Počítá se s domácí sítí. Appka nemá přihlašování a tenhle skript ji nijak
# nezabezpečuje; do internetu ji nepouštěj.
set -euo pipefail

APP="Kostky"
GITEA="${GITEA:-https://gitea.spacilovi.eu}"
REPO="${REPO:-david-spacil/dice-counter}"

# Výchozí hodnoty. Všechny se dají přebít proměnnou prostředí, třeba:
#     MEMORY=1024 STORAGE=local-zfs bash -c "$(curl -fsSL ...)"
CT_HOSTNAME="${CT_HOSTNAME:-kostky}"
CORES="${CORES:-1}"
MEMORY="${MEMORY:-512}"
DISK="${DISK:-4}"
STORAGE="${STORAGE:-}"
TEMPLATE_STORAGE="${TEMPLATE_STORAGE:-local}"
BRIDGE="${BRIDGE:-vmbr0}"
PORT="${PORT:-8000}"
UNPRIVILEGED="${UNPRIVILEGED:-1}"
OSVERSION="${OSVERSION:-13}"
VERSION="${VERSION:-}"          # prázdné = poslední vydání

# --- výpisy ------------------------------------------------------------------

msg() { echo -e "\e[1;34m  →\e[0m $*"; }
ok()  { echo -e "\e[1;32m  ✓\e[0m $*"; }
die() { echo -e "\e[1;31m  ✗\e[0m $*" >&2; exit 1; }

header() {
    echo
    echo -e "\e[1;36m  $APP\e[0m — počitadlo kostek do LXC"
    echo -e "  \e[2m$GITEA/$REPO\e[0m"
    echo
}

# --- instalátor, který poběží uvnitř kontejneru ------------------------------
#
# Je tu jako text schválně. Skript se pouští i rourou z curlu, kdy na disku
# hostitele žádný soubor není a nebylo by co poslat dovnitř. Uvozovky kolem
# 'INSTALL' jsou podstatné: nic z toho se tady nesmí rozvinout, všechny
# proměnné patří až tomu, co poběží v kontejneru.
#
# Vypsat se dá i samostatně: `bash pve-kostky.sh instalator > install.sh`,
# což se hodí, když chceš appku dostat do kontejneru, který sis založil sám.
installer() {
cat <<'INSTALL'
#!/usr/bin/env bash
# Instalace počitadla uvnitř kontejneru. O Proxmoxu nic neví, takže se dá
# pustit v jakémkoli Debianu. Je idempotentní — druhé spuštění jen vymění
# binárku za nejnovější.
set -euo pipefail

GITEA="${GITEA:-https://gitea.spacilovi.eu}"
REPO="${REPO:-david-spacil/dice-counter}"
PORT="${PORT:-8000}"
VERSION="${VERSION:-}"

USER_NAME=kostky
HOME_DIR=/opt/kostky
DATA_DIR=/var/lib/kostky

msg() { echo -e "\e[1;34m  →\e[0m $*"; }
ok()  { echo -e "\e[1;32m  ✓\e[0m $*"; }
die() { echo -e "\e[1;31m  ✗\e[0m $*" >&2; exit 1; }

case "$(dpkg --print-architecture)" in
    amd64) ASSET=kostky-linux-x86_64 ;;
    arm64) ASSET=kostky-linux-arm64 ;;
    *)     die "Pro architekturu $(dpkg --print-architecture) binárka není." ;;
esac

msg "Doinstalovávám, co je potřeba ke stažení"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl ca-certificates >/dev/null
ok "Základ je hotový"

if [ -z "$VERSION" ]; then
    msg "Zjišťuji poslední vydanou verzi"
    # Jen tag; adresa přílohy se z něj složí, takže tu nepotřebujeme jq.
    VERSION=$(curl -fsSL "$GITEA/api/v1/repos/$REPO/releases/latest" \
        | grep -o '"tag_name":[[:space:]]*"[^"]*"' | head -1 | cut -d'"' -f4)
    [ -n "$VERSION" ] || die "Nepodařilo se zjistit poslední verzi z $GITEA."
fi
ok "Instaluje se $VERSION ($ASSET)"

BASE="$GITEA/$REPO/releases/download/$VERSION"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

msg "Stahuji binárku"
curl -fsSL -o "$TMP/$ASSET" "$BASE/$ASSET" \
    || die "$ASSET pro $VERSION na releasu není. Vydání pro tuhle architekturu možná ještě neproběhlo."
curl -fsSL -o "$TMP/$ASSET.sha256" "$BASE/$ASSET.sha256" \
    || die "Chybí kontrolní součet — radši nic neinstaluju."

msg "Ověřuji kontrolní součet"
( cd "$TMP" && sha256sum -c "$ASSET.sha256" >/dev/null ) \
    || die "Kontrolní součet nesedí. Stažený soubor zahazuju."
ok "Součet sedí"

id -u "$USER_NAME" >/dev/null 2>&1 \
    || useradd --system --home-dir "$HOME_DIR" --shell /usr/sbin/nologin "$USER_NAME"

install -d -o root -g root -m 755 "$HOME_DIR"

# Zastavit se dá jen to, co běží — při první instalaci služba ještě není.
if systemctl is-active --quiet kostky; then
    systemctl stop kostky
fi

install -o root -g root -m 755 "$TMP/$ASSET" "$HOME_DIR/kostky"
echo "$VERSION" > "$HOME_DIR/verze"
ok "Binárka je na místě"

msg "Zapisuji službu"
cat > /etc/systemd/system/kostky.service <<EOF
[Unit]
Description=Počitadlo kostek
Documentation=$GITEA/$REPO
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER_NAME
Environment=DICE_DB=$DATA_DIR/dice.db
Environment=DICE_PORT=$PORT
ExecStart=$HOME_DIR/kostky
Restart=on-failure
RestartSec=5

# Databáze je jediné, co appka potřebuje mít zapisovatelné. StateDirectory ji
# založí a předá správnému uživateli, takže se tu nemusí nic chownovat.
StateDirectory=kostky
ReadWritePaths=$DATA_DIR

NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
# Binárka se při každém startu rozbaluje do /tmp; tady do vlastního, ne do
# sdíleného.
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --quiet --now kostky
ok "Služba běží"

msg "Čekám, až začne odpovídat"
for _ in $(seq 30); do
    curl -fsS -o /dev/null "http://127.0.0.1:$PORT/" 2>/dev/null && break
    sleep 1
done
curl -fsS -o /dev/null "http://127.0.0.1:$PORT/" \
    || die "Služba nastartovala, ale neodpovídá. Mrkni na journalctl -u kostky."

# Verzi bereme ze souboru, ne z binárky. Starší vydání --version neumí
# a místo výpisu by nastartovala server, který by tenhle skript zavěsil.
ok "Počitadlo $(cat "$HOME_DIR/verze") odpovídá na portu $PORT"
INSTALL
}

# --- společné části ----------------------------------------------------------

install_into() {
    local ctid="$1" tmp
    tmp=$(mktemp)
    installer > "$tmp"

    msg "Posílám instalátor do kontejneru $ctid"
    pct push "$ctid" "$tmp" /root/kostky-install.sh --perms 0755
    rm -f "$tmp"

    pct exec "$ctid" -- env PORT="$PORT" GITEA="$GITEA" REPO="$REPO" \
        VERSION="$VERSION" bash /root/kostky-install.sh
}

address_of() {
    pct exec "$1" -- hostname -I 2>/dev/null | awk '{print $1}'
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
    echo -e "  Konzole:   pct enter $ctid"
    echo -e "  Zrušit:    pct stop $ctid \&\& pct destroy $ctid\e[0m"
    echo
}

# --- co se má vlastně dělat --------------------------------------------------
#
# Rourou z curlu se argumenty předávají mizerně, tak jde všechno i proměnnou:
# MODE=update CTID=123. Ze souboru funguje i `bash pve-kostky.sh update 123`.
MODE="${MODE:-${1:-create}}"
[ "$MODE" = "update" ] && CTID="${CTID:-${2:-}}"

if [ "$MODE" = "instalator" ]; then
    installer
    exit 0
fi

command -v pct >/dev/null || die "Tohle patří na uzel Proxmoxu — pct tu není."
[ "$(id -u)" -eq 0 ] || die "Spusť to jako root."

# --- aktualizace -------------------------------------------------------------

if [ "$MODE" = "update" ]; then
    [ -n "${CTID:-}" ] || die "Řekni který: CTID=123 MODE=update ..."
    pct status "$CTID" >/dev/null 2>&1 || die "Kontejner $CTID neexistuje."

    header
    if [ "$(pct status "$CTID")" != "status: running" ]; then
        msg "Startuji kontejner"
        pct start "$CTID"
        sleep 5
    fi

    install_into "$CTID"
    hotovo "$CTID"
    exit 0
fi

# --- nový kontejner ----------------------------------------------------------

header

# Úložiště se nehádá. local-lvm na ZFS instalacích neexistuje a pct create by
# spadlo až po půlce práce, tak se radši zeptáme systému, co tu opravdu je.
if [ -z "$STORAGE" ]; then
    STORAGE=$(pvesm status -content rootdir 2>/dev/null \
        | awk 'NR>1 && $3=="active" {print $1; exit}')
    [ -n "$STORAGE" ] || die "Nenašel jsem úložiště pro kontejnery. Zadej STORAGE=<jméno>; co máš, ukáže pvesm status."
    msg "Úložiště: $STORAGE (nalezeno automaticky)"
else
    pvesm status -content rootdir 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx "$STORAGE" \
        || die "Úložiště $STORAGE pro kontejnery nesedí. Co máš, ukáže: pvesm status -content rootdir"
    msg "Úložiště: $STORAGE"
fi

CTID="${CTID:-$(pvesh get /cluster/nextid)}"
msg "Kontejner dostane číslo $CTID"

msg "Hledám šablonu Debianu $OSVERSION"
pveam update >/dev/null 2>&1 || true
TEMPLATE=$(pveam available --section system \
    | awk '{print $2}' | grep "^debian-${OSVERSION}-standard" | sort -V | tail -1)
[ -n "$TEMPLATE" ] || die "Šablona pro Debian $OSVERSION není k dispozici."

if ! pveam list "$TEMPLATE_STORAGE" 2>/dev/null | grep -q "$TEMPLATE"; then
    msg "Stahuji $TEMPLATE (asi 120 MB, chvíli to trvá)"
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
    --description "$APP — $GITEA/$REPO" >/dev/null
ok "Kontejner $CTID založen"

msg "Startuji"
pct start "$CTID"

msg "Čekám na síť"
for _ in $(seq 60); do
    if [ -n "$(address_of "$CTID")" ] \
        && pct exec "$CTID" -- getent hosts deb.debian.org >/dev/null 2>&1; then
        break
    fi
    sleep 2
done
[ -n "$(address_of "$CTID")" ] || die "Kontejner nedostal adresu. Sedí bridge $BRIDGE?"
ok "Adresa $(address_of "$CTID")"

install_into "$CTID"
hotovo "$CTID"
