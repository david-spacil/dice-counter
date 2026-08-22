import io

import console


class Proud:
    """Náhrada za výstup, která si pamatuje, na co ji přepnuli."""

    def __init__(self):
        self.encoding = "cp1252"
        self.errors = "strict"
        self.line_buffering = False

    def reconfigure(self, encoding, errors, line_buffering=False):
        self.encoding = encoding
        self.errors = errors
        self.line_buffering = line_buffering


def test_vystup_se_prepne_na_utf8(monkeypatch):
    out, err = Proud(), Proud()
    monkeypatch.setattr(console.sys, "stdout", out)
    monkeypatch.setattr(console.sys, "stderr", err)

    console.utf8()

    assert (out.encoding, out.errors) == ("utf-8", "replace")
    assert (err.encoding, err.errors) == ("utf-8", "replace")
    assert out.line_buffering and err.line_buffering


def test_cestina_projde_i_pres_cp1252(monkeypatch):
    """Přesně to, na čem umřela první windowsová binárka."""
    surovy = io.BytesIO()
    proud = io.TextIOWrapper(surovy, encoding="cp1252")
    monkeypatch.setattr(console.sys, "stdout", proud)
    monkeypatch.setattr(console.sys, "stderr", proud)

    console.utf8()
    print("Počitadlo je dostupné na:", file=console.sys.stdout)
    console.sys.stdout.flush()

    assert "Počitadlo je dostupné" in surovy.getvalue().decode("utf-8")


def test_proud_bez_reconfigure_se_prezije(monkeypatch):
    """Zabalený výstup reconfigure mít nemusí; padat kvůli tomu nesmíme."""
    monkeypatch.setattr(console.sys, "stdout", object())
    monkeypatch.setattr(console.sys, "stderr", object())

    console.utf8()


def test_hlaska_je_v_souboru_hned(tmp_path, monkeypatch):
    """Server běží dál, takže na vyprázdnění bufferu při konci se čekat nedá."""
    cesta = tmp_path / "server.log"
    with cesta.open("w", encoding="utf-8") as soubor:
        monkeypatch.setattr(console.sys, "stdout", soubor)
        monkeypatch.setattr(console.sys, "stderr", soubor)

        console.utf8()
        print("Počitadlo je dostupné na:", file=console.sys.stdout)

        # Bez zavření souboru — přesně jako u běžícího serveru.
        assert "Počitadlo je dostupné" in cesta.read_text(encoding="utf-8")
