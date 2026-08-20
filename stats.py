"""Statistiky napříč hrami.

Dvě různé obrazovky, protože odpovídají na jiné otázky: síň slávy sbírá
rekordy, kariéra ukazuje, kdo je dlouhodobě dobrý.

Vědomě tu není celkový součet bodů napříč hrami — cílové skóre je u každé hry
jiné, hry nejsou srovnatelné a taková metrika by odměňovala jen toho, kdo hrál
nejvíc.
"""

import sqlite3

import storage

# Celkové skóre hráče ve hře: součet tahů po posledním vynulování.
# Stejné pravidlo jako v core.Game.totals(), jen vyjádřené v SQL.
TOTALS = """
WITH last_reset AS (
    SELECT game_id, player_id, MAX(id) AS reset_id
    FROM turns
    WHERE reset = 1
    GROUP BY game_id, player_id
),
totals AS (
    SELECT gp.game_id,
           gp.player_id,
           COALESCE((
               SELECT SUM(t.value)
               FROM turns t
               LEFT JOIN last_reset lr
                      ON lr.game_id = t.game_id AND lr.player_id = t.player_id
               WHERE t.game_id = gp.game_id
                 AND t.player_id = gp.player_id
                 AND (lr.reset_id IS NULL OR t.id > lr.reset_id)
           ), 0) AS total
    FROM game_players gp
)
"""


def records(conn: sqlite3.Connection) -> dict:
    """Síň slávy — tři rekordy, které jde překonat."""
    best_turn = conn.execute("""
        SELECT p.name, t.value, t.game_id, t.at
        FROM turns t
        JOIN players p ON p.id = t.player_id
        ORDER BY t.value DESC, t.id ASC
        LIMIT 1
    """).fetchone()

    best_score = conn.execute(TOTALS + """
        SELECT p.name, totals.total, g.id AS game_id, g.finished_at
        FROM totals
        JOIN games g ON g.id = totals.game_id
        JOIN players p ON p.id = totals.player_id
        WHERE g.status = ?
        ORDER BY totals.total DESC
        LIMIT 1
    """, (storage.STATUS_FINISHED,)).fetchone()

    fastest = conn.execute("""
        SELECT p.name, g.id AS game_id, MAX(t.round) AS rounds, g.finished_at
        FROM games g
        JOIN turns t ON t.game_id = g.id
        JOIN players p ON p.id = g.winner_id
        WHERE g.status = ?
        GROUP BY g.id
        ORDER BY rounds ASC, g.id ASC
        LIMIT 1
    """, (storage.STATUS_FINISHED,)).fetchone()

    return {"best_turn": best_turn, "best_score": best_score, "fastest": fastest}


def careers(conn: sqlite3.Connection) -> list[dict]:
    """Kdo je dlouhodobě dobrý. Počítají se jen dohrané hry."""
    placings = conn.execute(TOTALS + """
        , ranked AS (
            SELECT totals.game_id,
                   totals.player_id,
                   RANK() OVER (PARTITION BY totals.game_id
                                ORDER BY totals.total DESC) AS placing
            FROM totals
            JOIN games g ON g.id = totals.game_id
            WHERE g.status = ?
        )
        SELECT r.player_id,
               p.name,
               COUNT(*) AS games,
               SUM(CASE WHEN g.winner_id = r.player_id THEN 1 ELSE 0 END) AS wins,
               AVG(r.placing) AS placing
        FROM ranked r
        JOIN players p ON p.id = r.player_id
        JOIN games g ON g.id = r.game_id
        GROUP BY r.player_id
    """, (storage.STATUS_FINISHED,)).fetchall()

    turn_stats = conn.execute("""
        SELECT t.player_id,
               AVG(t.value) AS per_turn,
               SUM(t.reset) AS wipeouts
        FROM turns t
        JOIN games g ON g.id = t.game_id
        WHERE g.status = ?
        GROUP BY t.player_id
    """, (storage.STATUS_FINISHED,)).fetchall()

    by_player = {row["player_id"]: row for row in turn_stats}

    table = []
    for row in placings:
        turns = by_player.get(row["player_id"])
        table.append({
            "name": row["name"],
            "games": row["games"],
            "wins": row["wins"],
            "share": row["wins"] / row["games"] if row["games"] else 0,
            "placing": row["placing"],
            "per_turn": turns["per_turn"] if turns else 0,
            "wipeouts": turns["wipeouts"] if turns else 0,
        })

    table.sort(key=lambda r: (-r["share"], r["placing"], -r["games"]))
    return table
