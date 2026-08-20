"""Pravidla hry v kostky.

Modul záměrně nic nevypisuje, na nic se neptá a nic neukládá — drží jen stav
hry a pravidla nad ním. Díky tomu ho může sdílet CLI i webová aplikace a dá se
testovat bez simulování vstupu.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

FINAL_SCORE: int = 10000

# Kolik nulových tahů po sobě hráči vynuluje skóre.
ZEROS_TO_RESET: int = 3


@dataclass
class Turn:
    """Jeden zápis skóre.

    Vynulování po třech nulách se ukládá jako hodnota 0 s příznakem `reset`,
    ne jako záporný tah — do historie tak nepadají čísla, která nikdo nehodil,
    a statistiky nad tahy zůstávají pravdivé.
    """

    player: str
    round: int
    value: int
    reset: bool = False
    at: datetime = field(default_factory=datetime.now)


@dataclass
class TurnResult:
    """Co se stalo po zapsání tahu."""

    turn: Turn
    was_reset: bool
    winner: str = ""


class GameOver(Exception):
    """Zápis do hry, která už má vítěze."""


class Game:
    def __init__(self, names: list[str], final_score: int = FINAL_SCORE,
                 turns: list[Turn] | None = None) -> None:
        if not names:
            raise ValueError("Hra potřebuje alespoň jednoho hráče.")
        if len(set(names)) != len(names):
            raise ValueError("Jména hráčů musí být unikátní.")

        self.names: list[str] = list(names)
        self.final_score: int = final_score
        self.turns: list[Turn] = list(turns) if turns else []

    @property
    def first(self) -> str:
        return self.names[0]

    @property
    def current_player(self) -> str:
        """Hráči se střídají dokola, takže tah plyne z počtu zápisů."""
        return self.names[len(self.turns) % len(self.names)]

    @property
    def round_number(self) -> int:
        return len(self.turns) // len(self.names) + 1

    @property
    def round_complete(self) -> bool:
        """True, když všichni odehráli stejný počet tahů."""
        return bool(self.turns) and len(self.turns) % len(self.names) == 0

    @property
    def winner(self) -> str:
        """Vítěz se vyhlašuje jen po dokončeném kole, ne uprostřed."""
        return self.check_win() if self.round_complete else ""

    @property
    def finished(self) -> bool:
        return bool(self.winner)

    def turns_of(self, player: str) -> list[Turn]:
        return [t for t in self.turns if t.player == player]

    def totals(self) -> dict[str, int]:
        """Součty se nikdy neukládají, vždy se počítají z tahů."""
        result = {name: 0 for name in self.names}
        for turn in self.turns:
            if turn.reset:
                result[turn.player] = 0
            else:
                result[turn.player] += turn.value
        return result

    def zero_streak(self, player: str) -> int:
        """Počet nul za sebou od posledního vynulování.

        Živí pravidlo i indikátor "x"/"xx". Počítání se na vynulovacím tahu
        zastaví, takže po vynulování začíná hráč zase od nuly.
        """
        streak = 0
        for turn in reversed(self.turns_of(player)):
            if turn.reset or turn.value != 0:
                break
            streak += 1
        return streak

    def add_score(self, value: int) -> TurnResult:
        if self.finished:
            raise GameOver("Hra už má vítěze.")

        player = self.current_player
        reset = value == 0 and self.zero_streak(player) >= ZEROS_TO_RESET - 1

        turn = Turn(player=player, round=self.round_number, value=value, reset=reset)
        self.turns.append(turn)

        return TurnResult(turn=turn, was_reset=reset, winner=self.winner)

    def undo(self) -> Turn | None:
        """Vrátí poslední zápis. Dá se opakovat.

        Protože jsou součty odvozené, stačí tah zahodit — platí to i pro
        vracení vynulování.
        """
        return self.turns.pop() if self.turns else None

    def check_win(self) -> str:
        """Jméno vítěze, nebo prázdno když se hraje dál.

        Při remíze na prvním místě vítěz není a hraje se dál.
        """
        totals = self.totals()
        over_limit = {n: v for n, v in totals.items() if v >= self.final_score}
        if not over_limit:
            return ""

        ranked = sorted(over_limit.items(), key=lambda x: x[1], reverse=True)
        counts = Counter(value for _, value in ranked)
        top_name, top_value = ranked[0]

        return top_name if counts[top_value] == 1 else ""

    def standings(self) -> list[tuple[int, str, int]]:
        """Pořadí, jméno a skóre — seřazeno od nejlepšího."""
        totals = self.totals()
        ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)
        return [(i + 1, name, value) for i, (name, value) in enumerate(ranked)]

    def rounds(self) -> list[tuple[int, dict[str, Turn | None]]]:
        """Zápisník po kolech pro tabuli: [(číslo kola, {hráč: tah nebo None})]."""
        result: list[tuple[int, dict[str, Turn | None]]] = []
        for index in range(0, len(self.turns), len(self.names)):
            chunk = self.turns[index:index + len(self.names)]
            by_player: dict[str, Turn | None] = {name: None for name in self.names}
            for turn in chunk:
                by_player[turn.player] = turn
            result.append((index // len(self.names) + 1, by_player))
        return result
