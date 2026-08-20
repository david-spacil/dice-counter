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
