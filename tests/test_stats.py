import pytest

import stats
import storage


@pytest.fixture
def conn(tmp_path):
    connection = storage.connect(tmp_path / "test.db")
    yield connection
    connection.close()


def play(conn, names, final_score, values, finish=True):
    game_id = storage.create_game(conn, names, final_score)
    game = storage.load_game(conn, game_id)
    for value in values:
        storage.add_turn(conn, game_id, game.add_score(value).turn)
    if finish and game.winner:
        storage.finish_game(conn, game_id, game.winner)
    return game_id


def by_name(table):
    return {row["name"]: row for row in table}


def test_prazdna_sin_slavy(conn):
    found = stats.records(conn)

    assert found["best_turn"] is None
    assert found["best_score"] is None
    assert found["fastest"] is None
    assert stats.careers(conn) == []


def test_rekordy(conn):
    play(conn, ["Adam", "Eva"], 1000, [600, 200, 500, 100])

    found = stats.records(conn)

    assert found["best_turn"]["name"] == "Adam"
    assert found["best_turn"]["value"] == 600
    assert found["best_score"]["name"] == "Adam"
    assert found["best_score"]["total"] == 1100
    assert found["fastest"]["name"] == "Adam"
    assert found["fastest"]["rounds"] == 2


def test_kariera_pocita_vyhry_a_uspesnost(conn):
    play(conn, ["Adam", "Eva"], 1000, [600, 200, 500, 100])
    play(conn, ["Adam", "Eva"], 1000, [100, 600, 200, 500])

    table = by_name(stats.careers(conn))

    assert table["Adam"]["games"] == 2
    assert table["Adam"]["wins"] == 1
    assert table["Adam"]["share"] == 0.5
    assert table["Eva"]["wins"] == 1


def test_nedohrane_hry_se_nepocitaji(conn):
    play(conn, ["Adam", "Eva"], 1000, [600, 200, 500, 100])
    play(conn, ["Adam", "Eva"], 5000, [100, 100], finish=False)

    table = by_name(stats.careers(conn))

    assert table["Adam"]["games"] == 1


def test_vynulovani_se_pocita(conn):
    # Eva vyhraje, Adam se cestou třikrát vynuluje.
    play(conn, ["Adam", "Eva"], 1000, [300, 400, 0, 300, 0, 200, 0, 500])

    table = by_name(stats.careers(conn))

    assert table["Adam"]["wipeouts"] == 1
    assert table["Eva"]["wipeouts"] == 0


def test_prumerne_poradi(conn):
    play(conn, ["Adam", "Eva", "Petr"], 1000, [600, 300, 100, 500, 200, 50])

    table = by_name(stats.careers(conn))

    assert table["Adam"]["placing"] == 1
    assert table["Eva"]["placing"] == 2
    assert table["Petr"]["placing"] == 3


def test_soucty_v_sql_respektuji_vynulovani(conn):
    """SQL musí počítat celkové skóre stejně jako core.Game.totals()."""
    game_id = play(conn, ["Adam", "Eva"], 1000, [300, 100, 0, 100, 0, 100, 0, 900])

    game = storage.load_game(conn, game_id)
    best = stats.records(conn)["best_score"]

    assert game.totals()["Adam"] == 0
    assert best["name"] == "Eva"
    assert best["total"] == game.totals()["Eva"]
