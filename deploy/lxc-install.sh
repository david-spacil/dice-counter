#!/usr/bin/env bash
# Instalace počitadla uvnitř kontejneru. Pouští se přes pve-kostky.sh, ne ručně.
#
# Oddělené od skriptu pro Proxmox schválně: tenhle běží uvnitř Debianu a nic
# o Proxmoxu neví, takže se dá pustit i v LXC, který sis založil sám, nebo ve
# virtuálu. Je idempotentní — po druhém spuštění máš nejnovější binárku.
set -euo pipefail

GITEA="${GITEA:-https://gitea.spacilovi.eu}"
REPO="${REPO:-david-spacil/dice-counter}"
PORT="${PORT:-8000}"
VERSION="${VERSION:-}"          # prázdné = poslední release

USER_NAME=kostky
HOME_DIR=/opt/kostky
DATA_DIR=/var/lib/kostky

msg() { echo -e "\e[1;34m  →\e[0m $*"; }
ok()  { echo -e "\e[1;32m  ✓\e[0m $*"; }
die() { echo -e "\e[1;31m  ✗\e[0m $*" >&2; exit 1; }

# --- co vlastně stahovat -----------------------------------------------------

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

# --- stažení a ověření -------------------------------------------------------

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

# --- uživatel, soubory, služba ----------------------------------------------

id -u "$USER_NAME" >/dev/null 2>&1 \
    || useradd --system --home-dir "$HOME_DIR" --shell /usr/sbin/nologin "$USER_NAME"

install -d -o root -g root -m 755 "$HOME_DIR"

# Služba se zastaví, jen když už běží — při první instalaci ještě neexistuje.
systemctl is-active --quiet kostky && systemctl stop kostky
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

# --- kontrola, že to opravdu jede -------------------------------------------

msg "Čekám, až začne odpovídat"
for _ in $(seq 30); do
    curl -fsS -o /dev/null "http://127.0.0.1:$PORT/" && break
    sleep 1
done
curl -fsS -o /dev/null "http://127.0.0.1:$PORT/" \
    || die "Služba nastartovala, ale neodpovídá. Mrkni na journalctl -u kostky."

# Verzi bereme ze souboru, ne z binárky. Starší vydání --version neumí
# a místo výpisu by nastartovala server, který by tenhle skript zavěsil.
ok "Počitadlo $(cat "$HOME_DIR/verze") odpovídá na portu $PORT"
