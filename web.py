# /// script
# requires-python = ">=3.11"
# dependencies = ["flask", "qrcode"]
# ///
"""Webové počitadlo pro domácí síť.

Telefon zapisuje skóre (`/game/<id>`), notebook ukazuje zápisník (`/board`).
Server-rendered HTML, formuláře přes POST/redirect/GET, žádný build step.
"""

import os
import socket
import sys
from pathlib import Path

import qrcode
from flask import (Flask, abort, g, redirect, render_template, request,
                   url_for)
from markupsafe import Markup

import net
import stats
import storage
from core import FINAL_SCORE, Game, GameOver

def bundled(folder: str) -> str:
    """Cesta k šablonám a stylům.

    Ze zdrojáků leží vedle tohoto souboru. V binárce je PyInstaller rozbalí
    do dočasného adresáře, na který ukazuje `sys._MEIPASS`.
    """
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return str(root / folder)


app = Flask(__name__,
            template_folder=bundled("templates"),
            static_folder=bundled("static"))

PORT = int(os.environ.get("DICE_PORT", 8000))

# Kolik kol tabule ukáže. Zbytek historie je na hráčích, ne na tabuli —
# ta má ukazovat stav, ne archiv.
BOARD_ROUNDS = 15


# --- připojení k databázi ---------------------------------------------------

def db():
    if "db" not in g:
        g.db = storage.connect()
    return g.db


@app.teardown_appcontext
def close_db(_exception):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


# --- adresa a QR kód --------------------------------------------------------

def primary_ip() -> str:
    """Adresa, na kterou tabule ukazuje. Prázdno, když se nedá zjistit."""
    found = net.addresses()
    return found[0].ip if found else ""


def links(path: str = "/") -> dict:
    """Adresy, na kterých je počitadlo dostupné, i s cílem pro QR kód.

    Hledá se při každém načtení — notebook se během večera může přesunout
    z domácí WiFi na hotspot a zpátky.
    """
    found = net.addresses()
    primary = found[0] if found else None

    return {
        "primary": primary,
        "others": found[1:],
        "port": PORT,
        "target": primary.url(PORT) + path if primary else "",
    }


def qr_svg(data: str) -> Markup:
    """QR jako SVG složené ze čtverečků — bez Pillow a bez práce s obrázky."""
    code = qrcode.QRCode(box_size=1, border=2)
    code.add_data(data)
    code.make(fit=True)
    matrix = code.get_matrix()
    size = len(matrix)

    rects = [
        f'<rect x="{x}" y="{y}" width="1" height="1"/>'
        for y, row in enumerate(matrix)
        for x, dark in enumerate(row) if dark
    ]

    return Markup(
        f'<svg class="qr" viewBox="0 0 {size} {size}" role="img" '
        f'aria-label="QR kód s adresou pro telefon" '
        f'shape-rendering="crispEdges">{"".join(rects)}</svg>'
    )


@app.template_filter("datum")
def datum(value: str) -> str:
    """Z ISO textu udělá 12. 8. 2026."""
    if not value:
        return ""
    den = value[:10].split("-")
    return f"{int(den[2])}. {int(den[1])}. {den[0]}"


@app.template_filter("qr")
def qr_filter(data: str) -> Markup:
    return qr_svg(data) if data else Markup("")


@app.template_filter("kola")
def kola(count: int) -> str:
    if count == 1:
        return "1 kolo"
    if 2 <= count <= 4:
        return f"{count} kola"
    return f"{count} kol"


@app.template_filter("cislo")
def cislo(value: int) -> str:
    """Tisíce se v češtině oddělují mezerou."""
    return f"{value:,}".replace(",", " ")


# --- zápisník ---------------------------------------------------------------

def scoresheet(game: Game) -> tuple[list[dict], int]:
    """Řádky zápisníku po kolech, od nejnovějšího.

    Naposledy odehrané kolo patří nahoru — po padesáti kolech by jinak bylo
    to podstatné mimo obrazovku. Vrací i počet kol, která se nevešla.

    Tahy zapsané před posledním vynulováním se přeškrtnou — přesně tak, jak
    by se škrtaly na papíře.
    """
    wiped_in_round = {}
    for turn in game.turns:
        if turn.reset:
            wiped_in_round[turn.player] = turn.round

    rows = []
    for number, by_player in game.rounds():
        cells = []
        for name in game.names:
            turn = by_player[name]
            cells.append({
                "value": None if turn is None else turn.value,
                "reset": turn is not None and turn.reset,
                "struck": turn is not None and turn.round < wiped_in_round.get(name, 0),
            })
        rows.append({"round": number, "cells": cells})

    rows.reverse()
    hidden = max(0, len(rows) - BOARD_ROUNDS)

    return rows[:BOARD_ROUNDS], hidden


def view(game: Game, game_id: int, row) -> dict:
    """Společný podklad pro zápisník i pro zadávací pohled."""
    totals = game.totals()
    winner = row["winner_name"] if row["status"] == storage.STATUS_FINISHED else ""
    rows, hidden = scoresheet(game)
    return {
        "game": game,
        "game_id": game_id,
        "row": row,
        "totals": totals,
        "rows": rows,
        "hidden": hidden,
        "streaks": {name: game.zero_streak(name) for name in game.names},
        "standings": game.standings(),
        "winner": winner,
        "current": "" if winner else game.current_player,
        "primary_ip": primary_ip(),
    }


def load(game_id: int) -> tuple[Game, "storage.sqlite3.Row"]:
    row = storage.game_row(db(), game_id)
    if row is None:
        abort(404)
    return storage.load_game(db(), game_id), row


# --- routy ------------------------------------------------------------------

@app.route("/")
def index():
    return render_template(
        "index.html",
        players=storage.known_players(db()),
        running=storage.running_game(db()),
        final_score=FINAL_SCORE,
    )


@app.post("/game")
def new_game():
    names = [n for n in request.form.getlist("player") if n.strip()]
    if not names:
        return redirect(url_for("index", chyba="Vyber aspoň jednoho hráče."))

    try:
        final_score = int(request.form.get("final_score") or FINAL_SCORE)
    except ValueError:
        return redirect(url_for("index", chyba="Cílové skóre musí být číslo."))

    try:
        game_id = storage.create_game(db(), names, final_score)
    except ValueError as exc:
        return redirect(url_for("index", chyba=str(exc)))

    return redirect(url_for("game_view", game_id=game_id))


@app.route("/game/<int:game_id>")
def game_view(game_id: int):
    game, row = load(game_id)
    return render_template("game.html", chyba=request.args.get("chyba", ""),
                           **view(game, game_id, row))


@app.post("/game/<int:game_id>/turn")
def add_turn(game_id: int):
    game, row = load(game_id)

    try:
        value = int(request.form.get("value", ""))
    except ValueError:
        return redirect(url_for("game_view", game_id=game_id,
                                chyba="Zadej skóre jako číslo."))

    try:
        result = game.add_score(value)
    except GameOver:
        return redirect(url_for("game_view", game_id=game_id))

    storage.add_turn(db(), game_id, result.turn)
    if result.winner:
        storage.finish_game(db(), game_id, result.winner)

    return redirect(url_for("game_view", game_id=game_id))


@app.post("/game/<int:game_id>/undo")
def undo(game_id: int):
    storage.undo_turn(db(), game_id)
    return redirect(url_for("game_view", game_id=game_id))


@app.post("/game/<int:game_id>/abandon")
def abandon(game_id: int):
    storage.abandon_game(db(), game_id)
    return redirect(url_for("index"))


@app.route("/board")
def board_redirect():
    game_id = storage.running_game(db())
    if game_id:
        return redirect(url_for("board", game_id=game_id))

    return render_template("board_idle.html", **links(url_for("index")))


@app.route("/board/<int:game_id>")
def board(game_id: int):
    game, row = load(game_id)
    return render_template("board.html",
                           **links(url_for("game_view", game_id=game_id)),
                           **view(game, game_id, row))


@app.route("/board/<int:game_id>/panel")
def board_panel(game_id: int):
    """Fragment, na který se tabule doptává každé dvě vteřiny."""
    game, row = load(game_id)
    return render_template("_panel.html", **view(game, game_id, row))


@app.route("/stats")
def hall():
    conn = db()
    return render_template("stats.html",
                           records=stats.records(conn),
                           careers=stats.careers(conn),
                           games=storage.recent_games(conn))


if __name__ == "__main__":
    found = net.addresses()

    if found:
        print("Počitadlo je dostupné na:")
        for address in found:
            mark = "→" if address.primary else " "
            print(f" {mark} {address.url(PORT):30} {address.label}")
        print(f"\nTabule na notebook: {found[0].url(PORT)}/board")
    else:
        print("Adresu se nepodařilo zjistit. Spusť server s DICE_HOST=<adresa>.")

    print(f"\nDatabáze: {storage.DB_PATH.resolve()}")

    app.run(host="0.0.0.0", port=PORT, threaded=True)
