import pytest

import storage
import web


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setenv("DICE_HOST", "192.168.0.10")
    web.app.config["TESTING"] = True
    with web.app.test_client() as client:
        yield client


def start_game(client, *names, final_score=1000):
    response = client.post("/game", data={"player": list(names),
                                          "final_score": final_score})
    assert response.status_code == 302
    return int(response.headers["Location"].rsplit("/", 1)[1])


def score(client, game_id, value):
    return client.post(f"/game/{game_id}/turn", data={"value": value})


def text(response):
    return response.get_data(as_text=True)


def test_prazdne_pocitadlo_nabizi_novou_hru(client):
    page = text(client.get("/"))

    assert "Kdo hraje" in page
    assert "Začít hru" in page


def test_zalozeni_hry_a_zapis_tahu(client):
    game_id = start_game(client, "Adam", "Eva")

    page = text(client.get(f"/game/{game_id}"))
    assert "Na tahu" in page
    assert "Adam" in page

    score(client, game_id, 450)

    page = text(client.get(f"/game/{game_id}"))
    assert "Eva" in page
    assert "450" in page


def test_znama_jmena_se_nabidnou_v_dalsi_hre(client):
    start_game(client, "Adam", "Eva")

    page = text(client.get("/"))

    assert 'data-name="Adam"' in page
    assert 'data-name="Eva"' in page


def test_rozehrana_hra_se_nabidne_k_pokracovani(client):
    game_id = start_game(client, "Adam", "Eva")

    page = text(client.get("/"))

    assert "Rozehraná hra" in page
    assert f"/game/{game_id}" in page


def test_neplatne_skore_neprojde(client):
    game_id = start_game(client, "Adam", "Eva")

    response = score(client, game_id, "hodně")

    assert "chyba" in response.headers["Location"]
    assert "Zadej skóre jako číslo." in text(client.get(response.headers["Location"]))


def test_vynulovani_se_v_zapisniku_vyznaci(client):
    game_id = start_game(client, "Adam")
    for value in (300, 0, 0, 0):
        score(client, game_id, value)

    panel = text(client.get(f"/board/{game_id}/panel"))

    assert "vynulováno" in panel
    assert "struck" in panel        # škrtnutý zápis před vynulováním


def test_vraceni_posledniho_zapisu(client):
    game_id = start_game(client, "Adam", "Eva")
    score(client, game_id, 450)
    score(client, game_id, 200)

    client.post(f"/game/{game_id}/undo")
    page = text(client.get(f"/game/{game_id}"))

    assert "Eva" in page
    assert "200" not in page


def test_varovani_pred_treti_nulou(client):
    game_id = start_game(client, "Adam")
    score(client, game_id, 300)
    score(client, game_id, 0)
    score(client, game_id, 0)

    assert "Ještě jedna nula" in text(client.get(f"/game/{game_id}"))


def test_dohrani_hry_vyhlasi_viteze(client):
    game_id = start_game(client, "Adam", "Eva", final_score=500)
    score(client, game_id, 500)
    score(client, game_id, 100)

    page = text(client.get(f"/game/{game_id}"))
    assert "Vyhrává" in page
    assert "Konec hry" in page

    assert storage.running_game(storage.connect(storage.DB_PATH)) is None


def test_do_dohrane_hry_uz_nejde_zapsat(client):
    game_id = start_game(client, "Adam", "Eva", final_score=500)
    score(client, game_id, 500)
    score(client, game_id, 100)

    score(client, game_id, 999)

    conn = storage.connect(storage.DB_PATH)
    assert storage.load_game(conn, game_id).totals()["Adam"] == 500


def test_remiza_hru_neukonci(client):
    game_id = start_game(client, "Adam", "Eva", final_score=500)
    score(client, game_id, 500)
    score(client, game_id, 500)

    page = text(client.get(f"/game/{game_id}"))

    assert "Na tahu" in page
    assert "Konec hry" not in page


def test_ukonceni_hry(client):
    game_id = start_game(client, "Adam", "Eva")

    client.post(f"/game/{game_id}/abandon")

    assert "Rozehraná hra" not in text(client.get("/"))


def test_tabule_ukazuje_qr_a_adresu(client):
    game_id = start_game(client, "Adam", "Eva")

    page = text(client.get(f"/board/{game_id}"))

    assert "<svg class=\"qr\"" in page
    assert "http://192.168.0.10:8000" in page


def test_tabule_bez_hry(client):
    page = text(client.get("/board"))

    assert "Zatím se nehraje" in page


def test_tabule_presmeruje_na_rozehranou_hru(client):
    game_id = start_game(client, "Adam", "Eva")

    response = client.get("/board")

    assert response.headers["Location"].endswith(f"/board/{game_id}")


def test_neexistujici_hra(client):
    assert client.get("/game/999").status_code == 404


def test_sin_slavy(client):
    game_id = start_game(client, "Adam", "Eva", final_score=500)
    score(client, game_id, 500)
    score(client, game_id, 100)

    page = text(client.get("/stats"))

    assert "Nejvyšší tah" in page
    assert "Kariéra" in page
    assert "Vyhrává Adam" in page


def test_sin_slavy_bez_her(client):
    assert "Rekordy přibudou po první hře" in text(client.get("/stats"))


def test_zapisnik_zacina_nejnovejsim_kolem(client):
    game_id = start_game(client, "Adam", final_score=99999)
    for value in (111, 222, 333):
        score(client, game_id, value)

    panel = text(client.get(f"/board/{game_id}/panel"))

    assert panel.index("333") < panel.index("222") < panel.index("111")


def test_soucty_jsou_nad_koly(client):
    game_id = start_game(client, "Adam", final_score=99999)
    score(client, game_id, 450)

    panel = text(client.get(f"/board/{game_id}/panel"))

    assert panel.index("Celkem") < panel.index(">450<")


def test_tabule_useka_starou_historii(client):
    game_id = start_game(client, "Adam", final_score=999999)
    for value in range(1, 31):
        score(client, game_id, value * 10)

    panel = text(client.get(f"/board/{game_id}/panel"))

    assert "a dalších 15 kol" in panel
    assert "300" in panel        # nejnovější kolo tam je
    assert ">150<" not in panel  # patnácté odspodu už ne


def test_kratka_hra_nic_neuseka(client):
    game_id = start_game(client, "Adam", final_score=99999)
    score(client, game_id, 100)

    assert "a dalších" not in text(client.get(f"/board/{game_id}/panel"))


@pytest.mark.parametrize("count, expected", [
    (1, "1 kolo"), (2, "2 kola"), (4, "4 kola"), (5, "5 kol"), (22, "22 kol"),
])
def test_sklonovani_kol(count, expected):
    assert web.kola(count) == expected
