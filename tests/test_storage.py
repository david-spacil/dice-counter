import sqlite3
from pathlib import Path

import pytest

import storage


@pytest.fixture
def conn(tmp_path):
    connection = storage.connect(tmp_path / "test.db")
    yield connection
    connection.close()


def test_stejne_jmeno_je_stejny_hrac(conn):
    """Arkádová identita: Adam z jedné hry je Adam i v další."""
    first = storage.create_game(conn, ["Adam", "Eva"])
    second = storage.create_game(conn, ["adam", "Petr"])

    adam_first = [p["id"] for p in storage.seating(conn, first) if p["name"] == "Adam"]
    adam_second = [p["id"] for p in storage.seating(conn, second)][0]

    assert adam_first[0] == adam_second


def test_normalizace_jmen():
    assert storage.normalize("  Adam ") == storage.normalize("adam")
    assert storage.normalize("Jan  Novák") == storage.normalize("jan novák")
    assert storage.normalize("Adam") != storage.normalize("Ádám")


def test_prejmenovani_se_propise_do_starych_her(conn):
    game_id = storage.create_game(conn, ["Adam", "Eva"])
    adam = storage.seating(conn, game_id)[0]["id"]

    storage.rename_player(conn, adam, "Adam Š.")

    assert [p["name"] for p in storage.seating(conn, game_id)] == ["Adam Š.", "Eva"]


def test_slouceni_hracu_po_preklepu(conn):
    good = storage.create_game(conn, ["Adam", "Eva"])
    typo = storage.create_game(conn, ["Adm", "Eva"])

    adam = storage.get_or_create_player(conn, "Adam")
    adm = storage.get_or_create_player(conn, "Adm")

    game = storage.load_game(conn, typo)
    storage.add_turn(conn, typo, game.add_score(150).turn)

    storage.merge_players(conn, adm, adam)

    assert [p["name"] for p in storage.seating(conn, typo)] == ["Adam", "Eva"]
    assert storage.load_game(conn, typo).totals()["Adam"] == 150
    assert [p["id"] for p in storage.known_players(conn)].count(adm) == 0
    assert storage.load_game(conn, good).totals() == {"Adam": 0, "Eva": 0}


def test_hra_se_nacte_zpatky_i_s_tahy(conn):
    game_id = storage.create_game(conn, ["Adam", "Eva"], final_score=500)
    game = storage.load_game(conn, game_id)

    for value in (100, 50, 0, 30):
        storage.add_turn(conn, game_id, game.add_score(value).turn)

    loaded = storage.load_game(conn, game_id)

    assert loaded.names == ["Adam", "Eva"]
    assert loaded.final_score == 500
    assert loaded.totals() == {"Adam": 100, "Eva": 80}
    assert loaded.current_player == "Adam"
    assert loaded.round_number == 3


def test_vynulovani_se_uklada_jako_nula_s_priznakem(conn):
    game_id = storage.create_game(conn, ["Adam"], final_score=500)
    game = storage.load_game(conn, game_id)

    for value in (300, 0, 0, 0):
        storage.add_turn(conn, game_id, game.add_score(value).turn)

    rows = conn.execute("SELECT value, reset FROM turns ORDER BY id").fetchall()

    assert [r["value"] for r in rows] == [300, 0, 0, 0]
    assert [r["reset"] for r in rows] == [0, 0, 0, 1]
    assert storage.load_game(conn, game_id).totals()["Adam"] == 0


def test_rozehrana_hra_se_najde_a_dokonci(conn):
    game_id = storage.create_game(conn, ["Adam", "Eva"], final_score=100)

    assert storage.running_game(conn) == game_id

    game = storage.load_game(conn, game_id)
    storage.add_turn(conn, game_id, game.add_score(100).turn)
    result = game.add_score(10)
    storage.add_turn(conn, game_id, result.turn)
    storage.finish_game(conn, game_id, result.winner)

    assert storage.running_game(conn) is None
    assert storage.game_row(conn, game_id)["status"] == storage.STATUS_FINISHED
    assert storage.game_row(conn, game_id)["winner_name"] == "Adam"


def test_undo_smaze_tah_a_vrati_hru_do_hry(conn):
    game_id = storage.create_game(conn, ["Adam", "Eva"], final_score=100)
    game = storage.load_game(conn, game_id)
    storage.add_turn(conn, game_id, game.add_score(100).turn)
    result = game.add_score(10)
    storage.add_turn(conn, game_id, result.turn)
    storage.finish_game(conn, game_id, result.winner)

    assert storage.undo_turn(conn, game_id)

    row = storage.game_row(conn, game_id)
    assert row["status"] == storage.STATUS_RUNNING
    assert row["winner_id"] is None
    assert storage.load_game(conn, game_id).current_player == "Eva"


def test_opustena_hra(conn):
    game_id = storage.create_game(conn, ["Adam", "Eva"])
    storage.abandon_game(conn, game_id)

    assert storage.running_game(conn) is None
    assert storage.game_row(conn, game_id)["status"] == storage.STATUS_ABANDONED


def test_hrac_nesmi_sedet_u_stolu_dvakrat(conn):
    with pytest.raises(ValueError):
        storage.create_game(conn, ["Adam", "adam"])


def test_prazdne_jmeno(conn):
    with pytest.raises(ValueError):
        storage.get_or_create_player(conn, "   ")


def test_umisteni_databaze_ze_zdrojaku(monkeypatch):
    """Ze zdrojáků se ukládá do pracovního adresáře."""
    monkeypatch.delenv("DICE_DB", raising=False)
    monkeypatch.delattr(storage.sys, "frozen", raising=False)

    assert storage.default_db() == Path("dice.db")


def test_umisteni_databaze_z_binarky(monkeypatch, tmp_path):
    """Binárka se rozbaluje do dočasného adresáře, databáze tam nesmí."""
    monkeypatch.delenv("DICE_DB", raising=False)
    monkeypatch.setattr(storage.sys, "frozen", True, raising=False)
    monkeypatch.setattr(storage.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert storage.default_db() == tmp_path / "kostky" / "dice.db"


def test_data_home_podle_systemu(monkeypatch, tmp_path):
    """Každý systém má svůj adresář na data; XDG je jen ten linuxový."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    monkeypatch.setattr(storage.sys, "platform", "win32")
    assert storage.data_home() == tmp_path / "AppData" / "Local"

    monkeypatch.setattr(storage.sys, "platform", "darwin")
    assert storage.data_home() == tmp_path / "Library" / "Application Support"

    monkeypatch.setattr(storage.sys, "platform", "linux")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert storage.data_home() == tmp_path / ".local" / "share"


def test_dice_db_prebije_oboje(monkeypatch, tmp_path):
    monkeypatch.setattr(storage.sys, "frozen", True, raising=False)
    monkeypatch.setenv("DICE_DB", str(tmp_path / "jinde.db"))

    assert storage.default_db() == tmp_path / "jinde.db"


def test_connect_zalozi_chybejici_adresar(tmp_path):
    conn = storage.connect(tmp_path / "novy" / "adresar" / "dice.db")
    conn.close()

    assert (tmp_path / "novy" / "adresar" / "dice.db").exists()


# --- verze schématu ---------------------------------------------------------

def verze(conn) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def test_nova_databaze_je_orazitkovana(tmp_path):
    conn = storage.connect(tmp_path / "nova.db")
    try:
        assert verze(conn) == storage.SCHEMA_VERSION
    finally:
        conn.close()


def test_databaze_z_doby_pred_verzovanim_prezije(tmp_path):
    """Přesně to, co lidem leží na disku z verzí 1.0 a 1.1.

    Tabulky má, razítko ne. Nesmí se ani přijít o data, ani spadnout.
    """
    path = tmp_path / "stara.db"
    stara = sqlite3.connect(path)
    stara.executescript(storage.SCHEMA)      # bez PRAGMA user_version
    stara.execute("INSERT INTO players (name, key, created_at) "
                  "VALUES ('Adam', 'adam', '2026-01-01T00:00:00')")
    stara.commit()
    stara.close()

    conn = storage.connect(path)
    try:
        assert verze(conn) == storage.SCHEMA_VERSION
        assert [p["name"] for p in storage.known_players(conn)] == ["Adam"]
    finally:
        conn.close()


def test_migrace_dojede_jen_ty_chybejici(tmp_path, monkeypatch):
    """Podruhé už krok proběhnout nesmí — jinak by ALTER TABLE spadl."""
    monkeypatch.setattr(storage, "MIGRATIONS",
                        ["ALTER TABLE players ADD COLUMN barva TEXT;"])
    monkeypatch.setattr(storage, "SCHEMA_VERSION", 2)

    path = tmp_path / "migrovana.db"
    conn = storage.connect(path)
    conn.close()

    conn = storage.connect(path)             # druhé spuštění téže verze
    try:
        assert verze(conn) == 2
        sloupce = [r[1] for r in conn.execute("PRAGMA table_info(players)")]
        assert "barva" in sloupce
    finally:
        conn.close()


def test_databaze_z_novejsi_verze_se_odmitne(tmp_path):
    """Radši srozumitelná hláška než tiše rozbitá data."""
    path = tmp_path / "budouci.db"
    conn = storage.connect(path)
    conn.execute(f"PRAGMA user_version = {storage.SCHEMA_VERSION + 1}")
    conn.commit()
    conn.close()

    with pytest.raises(RuntimeError, match="novější verze"):
        storage.connect(path)
