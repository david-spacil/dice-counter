"""Zjištění adres, na kterých je počitadlo dostupné.

Telefon a notebook se musí potkat na stejné síti a která to je, se během
večera mění — domácí WiFi, hotspot z telefonu, tailnet. Proto se adresy
hledají za běhu, hledá se jich víc a řadí se podle toho, jak pravděpodobně
povedou k cíli. Vybrat si může člověk; my jen nabídneme.

Nic se tu nezakazuje podle jména konkrétního rozhraní — rozhoduje rozsah
adresy a obecný typ rozhraní, ne to, co má kdo zrovna nainstalované.
"""

import ipaddress
import os
import socket
from dataclasses import dataclass

# Rozsah, ze kterého adresy přiděluje Tailscale (RFC 6598, CGNAT).
TAILNET = ipaddress.ip_network("100.64.0.0/10")

# Obvyklé předpony virtuálních rozhraní. Adresy z nich nezahazujeme, jen je
# řadíme nakonec — dostat se přes ně k počitadlu jde jen výjimečně.
VIRTUAL = ("docker", "br-", "virbr", "veth", "vmnet", "vboxnet", "tun", "tap")

KIND_LABELS = {
    "lan": "místní síť",
    "tailnet": "přes Tailscale",
    "public": "veřejná adresa",
    "virtual": "virtuální síť",
}

ORDER = {"lan": 0, "tailnet": 1, "public": 2, "virtual": 3}


@dataclass
class Address:
    ip: str
    interface: str
    kind: str
    primary: bool = False

    @property
    def label(self) -> str:
        return KIND_LABELS.get(self.kind, self.kind)

    def url(self, port: int) -> str:
        return f"http://{self.ip}:{port}"


def classify(ip: str, interface: str) -> str | None:
    """Typ adresy podle jejího rozsahu. None znamená nepoužitelná."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None

    if addr.is_loopback or addr.is_link_local or addr.is_unspecified:
        return None

    if addr in TAILNET:
        return "tailnet"

    if interface.startswith(VIRTUAL):
        return "virtual"

    return "lan" if addr.is_private else "public"


def rank(found: list[tuple[str, str]], primary: str | None) -> list[Address]:
    """Seřadí nalezené dvojice (rozhraní, adresa).

    První je adresa, přes kterou vede výchozí trasa — na té síti je telefon
    nejspíš taky. Zbytek podle typu. Čistá funkce, ať jde otestovat i to,
    co zrovna není v systému.
    """
    seen: dict[str, Address] = {}

    for interface, ip in found:
        kind = classify(ip, interface)
        if kind is None or ip in seen:
            continue
        seen[ip] = Address(ip=ip, interface=interface, kind=kind,
                           primary=(ip == primary))

    return sorted(seen.values(),
                  key=lambda a: (not a.primary, ORDER.get(a.kind, 9), a.ip))


def default_route_address() -> str | None:
    """Adresa rozhraní, kudy vede výchozí trasa.

    Připojení UDP socketu nic neposílá, jen si vyžádá směrování.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def _from_interfaces() -> list[tuple[str, str]]:
    """Adresy všech rozhraní. Linux, jen standardní knihovna."""
    try:
        import fcntl
        import struct
    except ImportError:
        return []

    siocgifaddr = 0x8915
    found = []

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for _index, name in socket.if_nameindex():
            try:
                packed = struct.pack("256s", name.encode()[:15])
                info = fcntl.ioctl(sock.fileno(), siocgifaddr, packed)
                found.append((name, socket.inet_ntoa(info[20:24])))
            except OSError:
                continue        # rozhraní bez IPv4 adresy

    return found


def _from_hostname() -> list[tuple[str, str]]:
    """Záloha pro systémy, kde předchozí cesta nefunguje."""
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        return []

    return [("", info[4][0]) for info in infos]


def addresses() -> list[Address]:
    """Kde všude je počitadlo k dispozici, od nejpravděpodobnější adresy.

    `DICE_HOST` má poslední slovo — když je nastavená, platí jen ona.
    """
    forced = os.environ.get("DICE_HOST")
    if forced:
        return [Address(ip=forced, interface="", kind="lan", primary=True)]

    primary = default_route_address()

    found = _from_interfaces() or _from_hostname()
    if primary and primary not in [ip for _name, ip in found]:
        found.append(("", primary))

    return rank(found, primary)
