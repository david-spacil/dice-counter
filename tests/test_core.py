import pytest

from core import Game, GameOver


def play(game: Game, *values: int) -> Game:
    """Odehraje tahy po sobě, jak by je zadával zapisovatel."""
    for value in values:
        game.add_score(value)
    return game


def test_tri_nuly_vynuluji_skore():
    game = Game(["A", "B"], final_score=1000)
    play(game, 200, 10, 0, 10, 0, 10)

    assert game.totals()["A"] == 200

    result = game.add_score(0)

    assert result.was_reset
    assert game.totals()["A"] == 0


def test_nenulovy_tah_prerusi_serii():
    game = Game(["A", "B"], final_score=1000)
    play(game, 0, 10, 0, 10, 50, 10)

    result = game.add_score(0)

    assert not result.was_reset
    assert game.totals()["A"] == 50


def test_po_vynulovani_zacina_serie_znovu():
    game = Game(["A"], final_score=1000)
    play(game, 100, 0, 0, 0)

    assert game.totals()["A"] == 0

    # Další dvě nuly ještě vynulovat nesmí — série se počítá od resetu.
    assert not game.add_score(0).was_reset
    assert not game.add_score(0).was_reset
    assert game.add_score(0).was_reset


def test_vynulovani_se_neuklada_jako_zaporny_tah():
    game = Game(["A"], final_score=1000)
    play(game, 300, 0, 0, 0)

    assert [t.value for t in game.turns] == [300, 0, 0, 0]
    assert [t.reset for t in game.turns] == [False, False, False, True]


def test_remiza_na_prvnim_miste_hru_nekonci():
    game = Game(["A", "B"], final_score=1000)
    play(game, 1000, 1000)

    assert game.round_complete
    assert game.check_win() == ""
    assert not game.finished


def test_vitez_az_po_dokoncenem_kole():
    game = Game(["A", "B"], final_score=1000)
    game.add_score(1000)

    # A je přes limit, ale B ještě nehrál.
    assert game.totals()["A"] == 1000
    assert game.winner == ""

    result = game.add_score(10)

    assert result.winner == "A"
    assert game.finished


def test_do_dohrane_hry_uz_nejde_zapsat():
    game = Game(["A", "B"], final_score=1000)
    play(game, 1000, 10)

    with pytest.raises(GameOver):
        game.add_score(50)


def test_undo_vrati_skore_i_hrace_na_tahu():
    game = Game(["A", "B"], final_score=1000)
    play(game, 100, 50)

    assert game.current_player == "A"

    game.add_score(70)

    assert game.current_player == "B"
    assert game.totals()["A"] == 170

    game.undo()

    assert game.current_player == "A"
    assert game.totals()["A"] == 100


def test_undo_pres_vynulovani_obnovi_puvodni_skore():
    game = Game(["A"], final_score=1000)
    play(game, 400, 0, 0, 0)

    assert game.totals()["A"] == 0

    game.undo()

    assert game.totals()["A"] == 400
    assert game.zero_streak("A") == 2


def test_undo_na_prazdne_hre():
    game = Game(["A"])

    assert game.undo() is None


def test_zero_streak():
    game = Game(["A"], final_score=1000)

    assert game.zero_streak("A") == 0

    game.add_score(0)
    assert game.zero_streak("A") == 1

    game.add_score(0)
    assert game.zero_streak("A") == 2

    game.add_score(0)
    assert game.zero_streak("A") == 0


def test_poradi_hracu_se_toci_dokola():
    game = Game(["A", "B", "C"])

    assert [game.current_player for _ in range(1)] == ["A"]
    assert game.round_number == 1

    play(game, 10, 10, 10)

    assert game.current_player == "A"
    assert game.round_number == 2


def test_standings_radi_od_nejlepsiho():
    game = Game(["A", "B", "C"])
    play(game, 10, 300, 50)

    assert game.standings() == [(1, "B", 300), (2, "C", 50), (3, "A", 10)]


def test_rounds_dela_zapisnik_po_kolech():
    game = Game(["A", "B"])
    play(game, 10, 20, 30)

    rounds = game.rounds()

    assert len(rounds) == 2
    assert rounds[0][0] == 1
    assert rounds[0][1]["A"].value == 10
    assert rounds[0][1]["B"].value == 20
    assert rounds[1][1]["A"].value == 30
    assert rounds[1][1]["B"] is None


def test_hra_potrebuje_hrace():
    with pytest.raises(ValueError):
        Game([])

    with pytest.raises(ValueError):
        Game(["A", "A"])
