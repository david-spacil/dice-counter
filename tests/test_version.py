"""Verze se musí poznat i z binárky, kde žádný git není."""

import pytest

import version


@pytest.fixture(autouse=True)
def bez_pameti():
    """`current()` si výsledek pamatuje; mezi testy je potřeba čistý stůl."""
    version.current.cache_clear()
    yield
    version.current.cache_clear()


def test_z_binarky_se_cte_pribaleny_soubor(monkeypatch, tmp_path):
    """V binárce leží verze.txt v dočasném adresáři vedle šablon."""
    (tmp_path / version.NAME).write_text("v9.9.9\n", encoding="utf-8")
    monkeypatch.setattr(version.sys, "frozen", True, raising=False)
    monkeypatch.setattr(version.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert version.current() == "v9.9.9"


def test_binarka_se_gitu_nepta(monkeypatch, tmp_path):
    """Na cizím počítači žádný repozitář není a ptát se nemá koho."""
    monkeypatch.setattr(version.sys, "frozen", True, raising=False)
    monkeypatch.setattr(version.sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(version, "described",
                        lambda: pytest.fail("binárka se ptala gitu"))

    assert version.current() == version.UNKNOWN


def test_ze_zdrojaku_ma_prednost_git(monkeypatch):
    monkeypatch.delattr(version.sys, "frozen", raising=False)
    monkeypatch.setattr(version, "described", lambda: "v1.2.3-4-gabcdef")
    monkeypatch.setattr(version, "bundled", lambda: "v1.0.0")

    assert version.current() == "v1.2.3-4-gabcdef"


def test_bez_gitu_a_bez_souboru_zbyde_neznama(monkeypatch):
    monkeypatch.delattr(version.sys, "frozen", raising=False)
    monkeypatch.setattr(version, "described", lambda: "")
    monkeypatch.setattr(version, "bundled", lambda: "")

    assert version.current() == version.UNKNOWN
