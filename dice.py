# /// script
# requires-python = ">=3.11"
# dependencies = ["tabulate"]
# ///
"""Počitadlo skóre v terminálu.

Pravidla žijí v `core.Game`, tenhle modul je jen vstup a výstup. Hraje se
v paměti, nic se neukládá — na historii je webová aplikace (`web.py`).
"""

from os import name, system

from tabulate import tabulate

import console
from core import FINAL_SCORE, Game

table_header = ["Hráč", "Skóre"]


def clear() -> None:
    _ = system('cls') if name == 'nt' else system('clear')


def char_create() -> tuple[list[str], int]:
    """Zeptá se na hráče a cílové skóre."""
    hraci: list[str] = []

    while True:
        inp: str = input("Zadejte jméno prvního hráče: ")
        if inp:
            hraci.append(inp)
            clear()
            print(f"Hráč/ka {inp} přidán(a).")
            break
        else:
            clear()
            print("Jméno nesmí být prázdné.")

    while True:
        inp = input("Zadejte jméno dalšího hráče (nebo nechte prázdné pro ukončení zadávání): ")
        if inp:
            if inp in hraci:
                clear()
                print("Je potřeba zadávat unikátní jména.")
            else:
                clear()
                hraci.append(inp)
                print(f"Hráč/ka {inp} přidán(a).")
        else:
            break

    final_score: int = FINAL_SCORE

    while True:
        inp = input("Zadejte finální skóre (nechte prázdné pro výchozích 10 000): ")
        if inp != "":
            try:
                inp_int: int = int(inp)
                final_score = inp_int
            except ValueError:
                print("Zadejte prosím platnou číselnou hodnotu.")
            else:
                break
        else:
            break

    return hraci, final_score


def table(game: Game) -> str:
    hraci_tab = []
    for hrac, hodnota in game.totals().items():
        if game.current_player == hrac:
            hrac = "> " + hrac
        hraci_tab.append([hrac, hodnota])

    return tabulate(hraci_tab, headers=table_header, tablefmt="fancy_grid")


def win(game: Game, winner: str) -> None:
    headers = ["Pořadí", "Hráč", "Skóre"]
    vysledky = tabulate(game.standings(), headers=headers, tablefmt="fancy_grid")

    print(f"Vítězem se stává {winner} s {game.totals()[winner]} body!")
    print("Díky za hru a zase příště.\n")

    print(vysledky)


def play(game: Game) -> None:
    while True:
        clear()
        print(table(game))

        pointer = game.current_player
        strikes: str = "x" * game.zero_streak(pointer)

        inp = input(f"Zadejte skóre hráče {pointer} "
                    f"({game.totals()[pointer]}{strikes}/{game.final_score}): ")
        try:
            inp_int = int(inp)
        except ValueError:
            clear()
            input("Zadejte prosím platnou číselnou hodnotu.")
            continue

        result = game.add_score(inp_int)

        if result.was_reset:
            clear()
            input("Po třech nulových hodech bylo vaše skóre vynulováno.")

        if result.winner:
            clear()
            win(game, result.winner)
            break


def main() -> None:
    clear()
    hraci, final_score = char_create()
    clear()
    print("Vytvoření hráči:", ", ".join(hraci))

    input("Stiskněte libovolnou klávesu pro pokračování. ")

    play(Game(hraci, final_score))


if __name__ == "__main__":
    console.utf8()
    main()
