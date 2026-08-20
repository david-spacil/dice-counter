"""Trvalé úložiště nad SQLite.

Ručně psané SQL nad pěti tabulkami, žádné ORM. Hry ukazují na `players.id`,
nikdy na jméno — přejmenování hráče se tím propíše i do starých her.

Součty se nikde neukládají; stav hry se rekonstruuje načtením tahů do
`core.Game`.
"""

import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from core import FINAL_SCORE, Game, Turn

DB_PATH = Path(os.environ.get("DICE_DB", "dice.db"))

STATUS_RUNNING = "probíhá"
STATUS_FINISHED = "dohráno"
STATUS_ABANDONED = "opuštěno"

SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    key        TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS games (
    id          INTEGER PRIMARY KEY,
    final_score INTEGER NOT NULL,
    status      TEXT NOT NULL,
    winner_id   INTEGER REFERENCES players(id),
    started_at  TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS game_players (
    game_id   INTEGER NOT NULL REFERENCES games(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    seat      INTEGER NOT NULL,
    PRIMARY KEY (game_id, player_id)
);

CREATE TABLE IF NOT EXISTS turns (
    id        INTEGER PRIMARY KEY,
    game_id   INTEGER NOT NULL REFERENCES games(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    round     INTEGER NOT NULL,
    value     INTEGER NOT NULL,
    reset     INTEGER NOT NULL DEFAULT 0,
    at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS turns_game ON turns(game_id, id);
"""


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def now() -> str:
    """Časy ukládáme jako ISO text — sqlite3 vlastní adaptéry pro datetime
    mezitím zavrhl."""
    return datetime.now().isoformat(timespec="seconds")


# --- hráči ------------------------------------------------------------------

def normalize(name: str) -> str:
    """Klíč pro párování jmen napříč hrami: Adam, adam i " Adam " je týž hráč."""
    return re.sub(r"\s+", " ", name).strip().casefold()


def get_or_create_player(conn: sqlite3.Connection, name: str) -> int:
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        raise ValueError("Jméno nesmí být prázdné.")

    key = normalize(name)
    row = conn.execute("SELECT id FROM players WHERE key = ?", (key,)).fetchone()
    if row:
        return row["id"]

    cursor = conn.execute(
        "INSERT INTO players (name, key, created_at) VALUES (?, ?, ?)",
        (name, key, now()),
    )
    conn.commit()
    return cursor.lastrowid


def known_players(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Známí hráči k odklikání, naposledy hrající první."""
    return conn.execute("""
        SELECT p.id, p.name, MAX(t.at) AS last_played
        FROM players p
        LEFT JOIN turns t ON t.player_id = p.id
        GROUP BY p.id
        ORDER BY last_played DESC, p.name COLLATE NOCASE
    """).fetchall()


def rename_player(conn: sqlite3.Connection, player_id: int, name: str) -> None:
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        raise ValueError("Jméno nesmí být prázdné.")

    conn.execute("UPDATE players SET name = ?, key = ? WHERE id = ?",
                 (name, normalize(name), player_id))
    conn.commit()


def merge_players(conn: sqlite3.Connection, source_id: int, target_id: int) -> None:
    """Sloučí hráče vzniklého překlepem do toho správného."""
    if source_id == target_id:
        return

    # Kdyby oba omylem hráli tutéž hru, druhé sedadlo zahodíme.
    conn.execute("""
        DELETE FROM game_players
        WHERE player_id = ?
          AND game_id IN (SELECT game_id FROM game_players WHERE player_id = ?)
    """, (source_id, target_id))

    conn.execute("UPDATE game_players SET player_id = ? WHERE player_id = ?",
                 (target_id, source_id))
    conn.execute("UPDATE turns SET player_id = ? WHERE player_id = ?",
                 (target_id, source_id))
    conn.execute("UPDATE games SET winner_id = ? WHERE winner_id = ?",
                 (target_id, source_id))
    conn.execute("DELETE FROM players WHERE id = ?", (source_id,))
    conn.commit()


# --- hry --------------------------------------------------------------------

def create_game(conn: sqlite3.Connection, names: list[str],
                final_score: int = FINAL_SCORE) -> int:
    """Založí hru. Pořadí jmen je pořadí u stolu."""
    ids = [get_or_create_player(conn, name) for name in names]
    if len(set(ids)) != len(ids):
        raise ValueError("Každý hráč může u stolu sedět jen jednou.")

    cursor = conn.execute(
        "INSERT INTO games (final_score, status, started_at) VALUES (?, ?, ?)",
        (final_score, STATUS_RUNNING, now()),
    )
    game_id = cursor.lastrowid

    conn.executemany(
        "INSERT INTO game_players (game_id, player_id, seat) VALUES (?, ?, ?)",
        [(game_id, player_id, seat) for seat, player_id in enumerate(ids)],
    )
    conn.commit()
    return game_id


def game_row(conn: sqlite3.Connection, game_id: int) -> sqlite3.Row | None:
    return conn.execute("""
        SELECT g.*, w.name AS winner_name
        FROM games g
        LEFT JOIN players w ON w.id = g.winner_id
        WHERE g.id = ?
    """, (game_id,)).fetchone()


def seating(conn: sqlite3.Connection, game_id: int) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT p.id, p.name
        FROM game_players gp
        JOIN players p ON p.id = gp.player_id
        WHERE gp.game_id = ?
        ORDER BY gp.seat
    """, (game_id,)).fetchall()


def load_game(conn: sqlite3.Connection, game_id: int) -> Game:
    """Rekonstruuje `core.Game` z uložených tahů."""
    row = game_row(conn, game_id)
    if row is None:
        raise LookupError(f"Hra {game_id} neexistuje.")

    names = [player["name"] for player in seating(conn, game_id)]

    turn_rows = conn.execute("""
        SELECT p.name, t.round, t.value, t.reset, t.at
        FROM turns t
        JOIN players p ON p.id = t.player_id
        WHERE t.game_id = ?
        ORDER BY t.id
    """, (game_id,)).fetchall()

    turns = [
        Turn(player=t["name"], round=t["round"], value=t["value"],
             reset=bool(t["reset"]), at=datetime.fromisoformat(t["at"]))
        for t in turn_rows
    ]

    return Game(names, final_score=row["final_score"], turns=turns)


def running_game(conn: sqlite3.Connection) -> int | None:
    """Poslední rozehraná hra — díky ní se dá po pádu serveru pokračovat."""
    row = conn.execute(
        "SELECT id FROM games WHERE status = ? ORDER BY id DESC LIMIT 1",
        (STATUS_RUNNING,),
    ).fetchone()
    return row["id"] if row else None


def recent_games(conn: sqlite3.Connection, limit: int = 20) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT g.id, g.final_score, g.status, g.started_at, g.finished_at,
               w.name AS winner_name,
               (SELECT COUNT(*) FROM game_players gp WHERE gp.game_id = g.id) AS players,
               (SELECT COUNT(*) FROM turns t WHERE t.game_id = g.id) AS turns
        FROM games g
        LEFT JOIN players w ON w.id = g.winner_id
        ORDER BY g.id DESC
        LIMIT ?
    """, (limit,)).fetchall()


# --- tahy -------------------------------------------------------------------

def add_turn(conn: sqlite3.Connection, game_id: int, turn: Turn) -> None:
    """Zapisuje se hned po každém tahu, ne až na konci hry."""
    row = conn.execute("""
        SELECT p.id
        FROM game_players gp
        JOIN players p ON p.id = gp.player_id
        WHERE gp.game_id = ? AND p.name = ?
    """, (game_id, turn.player)).fetchone()

    if row is None:
        raise LookupError(f"Hráč {turn.player} v této hře nehraje.")

    conn.execute("""
        INSERT INTO turns (game_id, player_id, round, value, reset, at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (game_id, row["id"], turn.round, turn.value, int(turn.reset),
          turn.at.isoformat(timespec="seconds")))
    conn.commit()


def undo_turn(conn: sqlite3.Connection, game_id: int) -> bool:
    """Zahodí poslední zápis. Dá se opakovat."""
    row = conn.execute(
        "SELECT id FROM turns WHERE game_id = ? ORDER BY id DESC LIMIT 1",
        (game_id,),
    ).fetchone()
    if row is None:
        return False

    conn.execute("DELETE FROM turns WHERE id = ?", (row["id"],))
    conn.execute(
        "UPDATE games SET status = ?, winner_id = NULL, finished_at = NULL WHERE id = ?",
        (STATUS_RUNNING, game_id),
    )
    conn.commit()
    return True


def finish_game(conn: sqlite3.Connection, game_id: int, winner: str) -> None:
    row = conn.execute("SELECT id FROM players WHERE key = ?",
                       (normalize(winner),)).fetchone()
    conn.execute(
        "UPDATE games SET status = ?, winner_id = ?, finished_at = ? WHERE id = ?",
        (STATUS_FINISHED, row["id"] if row else None, now(), game_id),
    )
    conn.commit()


def abandon_game(conn: sqlite3.Connection, game_id: int) -> None:
    """Nedohrané hry se nepočítají do statistik výher."""
    conn.execute(
        "UPDATE games SET status = ?, finished_at = ? WHERE id = ?",
        (STATUS_ABANDONED, now(), game_id),
    )
    conn.commit()
