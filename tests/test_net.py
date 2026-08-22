import pytest

import net


@pytest.mark.parametrize("ip, interface, expected", [
    ("127.0.0.1", "lo", None),              # loopback
    ("169.254.3.7", "wlp44s0", None),       # link-local, adresa bez DHCP
    ("0.0.0.0", "eth0", None),
    ("nesmysl", "eth0", None),
    ("192.168.1.20", "wlp44s0", "lan"),
    ("10.186.234.182", "wlp44s0", "lan"),   # hotspot z telefonu
    ("172.20.10.3", "en0", "lan"),          # hotspot z iPhonu
    ("100.91.0.24", "tailscale0", "tailnet"),
    ("172.17.0.1", "docker0", "virtual"),
    ("192.168.122.1", "virbr0", "virtual"),
    ("10.0.0.5", "br-2f1a798d", "virtual"),
    ("93.184.216.34", "eth0", "public"),
])
def test_klasifikace_podle_rozsahu(ip, interface, expected):
    assert net.classify(ip, interface) == expected


def test_tailnet_pozna_i_jine_rozhrani():
    """Rozhoduje rozsah adresy, ne jméno rozhraní."""
    assert net.classify("100.64.0.1", "eth0") == "tailnet"
    assert net.classify("100.127.255.254", "") == "tailnet"
    assert net.classify("100.128.0.1", "eth0") == "public"   # už mimo rozsah


def test_poradi_adres():
    found = [
        ("docker0", "172.17.0.1"),
        ("tailscale0", "100.91.0.24"),
        ("lo", "127.0.0.1"),
        ("wlp44s0", "10.186.234.182"),
        ("eth0", "192.168.1.20"),
    ]

    ranked = net.rank(found, primary="10.186.234.182")

    assert [a.ip for a in ranked] == [
        "10.186.234.182",   # výchozí trasa
        "192.168.1.20",     # ostatní místní sítě
        "100.91.0.24",      # tailnet funguje i napříč sítěmi
        "172.17.0.1",       # virtuální až nakonec
    ]
    assert ranked[0].primary
    assert not ranked[1].primary


def test_bez_vychozi_trasy_se_poradi_drzi_typu():
    found = [("docker0", "172.17.0.1"), ("wlp44s0", "192.168.1.20")]

    ranked = net.rank(found, primary=None)

    assert [a.ip for a in ranked] == ["192.168.1.20", "172.17.0.1"]
    assert not any(a.primary for a in ranked)


def test_duplicity_se_slucuji():
    found = [("wlp44s0", "10.0.0.5"), ("", "10.0.0.5")]

    assert len(net.rank(found, primary="10.0.0.5")) == 1


def test_zadna_pouzitelna_adresa():
    assert net.rank([("lo", "127.0.0.1")], primary=None) == []


def test_dice_host_ma_posledni_slovo(monkeypatch):
    monkeypatch.setenv("DICE_HOST", "192.168.5.5")

    found = net.addresses()

    assert [a.ip for a in found] == ["192.168.5.5"]
    assert found[0].primary


def test_url_a_popisek():
    address = net.Address(ip="10.0.0.5", interface="wlp44s0", kind="tailnet")

    assert address.url(8000) == "http://10.0.0.5:8000"
    assert address.label == "přes Tailscale"


def test_v_systemu_se_neco_najde():
    """Na stroji s libovolnou sítí musí vyjít aspoň jedna adresa."""
    found = net.addresses()

    assert all(net.classify(a.ip, a.interface) for a in found)
    assert len({a.ip for a in found}) == len(found)


IFCONFIG_MACOS = """\
lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384
\toptions=1203<RXCSUM,TXCSUM,TXSTATUS,SW_TIMESTAMP>
\tinet 127.0.0.1 netmask 0xff000000
\tinet6 ::1 prefixlen 128
gif0: flags=8010<POINTOPOINT,MULTICAST> mtu 1280
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
\tether 3c:22:fb:aa:bb:cc
\tinet6 fe80::14b0:6b1a:9e2f:1a4c%en0 prefixlen 64 secured scopeid 0xb
\tinet 192.168.0.42 netmask 0xffffff00 broadcast 192.168.0.255
\tmedia: autoselect
\tstatus: active
utun4: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST> mtu 1280
\tinet 100.99.98.97 --> 100.99.98.97 netmask 0xff000000
"""


def test_ifconfig_vytahne_rozhrani_a_adresy():
    """macOS na ioctl z Linuxu neslyší, tak se čte výstup ifconfigu."""
    assert net.parse_ifconfig(IFCONFIG_MACOS) == [
        ("lo0", "127.0.0.1"),
        ("en0", "192.168.0.42"),
        ("utun4", "100.99.98.97"),
    ]


def test_ifconfig_si_neplete_inet6_s_inet():
    """`inet6` začíná stejně jako `inet`; IPv6 adresy tudy projít nesmí."""
    assert net.parse_ifconfig("en0: flags=1\n\tinet6 fe80::1 prefixlen 64\n") == []


def test_adresy_z_ifconfigu_projdou_celym_retezem(monkeypatch):
    """Bez linuxového ioctl se sáhne po ifconfigu, teprve pak po hostname."""
    monkeypatch.delenv("DICE_HOST", raising=False)
    monkeypatch.setattr(net, "_from_interfaces", lambda: [])
    monkeypatch.setattr(net, "_from_ifconfig",
                        lambda: net.parse_ifconfig(IFCONFIG_MACOS))
    monkeypatch.setattr(net, "_from_hostname", lambda: pytest.fail("moc brzy"))
    monkeypatch.setattr(net, "default_route_address", lambda: "192.168.0.42")

    found = net.addresses()

    assert [a.ip for a in found] == ["192.168.0.42", "100.99.98.97"]
    assert found[0].primary and found[0].interface == "en0"
    assert found[1].kind == "tailnet"
