import sys
from collections import Counter
from os import name, system

from tabulate import tabulate

hraci = {}
score = {}
pointer = ""
first = ""
final_score = 10000

def clear() -> None:
    _ = system('cls') if name == 'nt' else system('clear') 

def char_create() -> bool:
    global pointer
    global first
    global final_score

    while True:
        inp: str = input("Zadejte jméno prvního hráče: ")
        if inp:
            hraci[inp] = []
            score[inp] = 0
            pointer = inp
            first = inp
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
                hraci[inp] = []
                score[inp] = 0
                print(f"Hráč/ka {inp} přidán(a).")
        else:
            break

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

    return True

def next_player() -> None:
    global pointer

    keys_iter = iter(hraci)
    for key in keys_iter:
        if key == pointer:
            nxt_key = next(keys_iter, first)
            break

    pointer = nxt_key

table_header = ["Hráč", "Skóre"]

def table():
    hraci_tab = []
    for h, h_val in score.items():
        hrac = h
        if pointer == h:
            hrac = "> "+h
        hraci_tab.append([hrac, h_val])

    return tabulate(hraci_tab, headers=table_header, tablefmt="fancy_grid")

def add_score(hrac, hodnota):
    if hodnota == 0:
        last_two = hraci[hrac][-2:]
        if len(last_two) > 1:
            last_two_sum = sum(last_two)
            if last_two_sum == 0:
                hodnota = -sum(hraci[hrac])
                clear()
                input("Po třech nulových hodech bylo vaše skóre vynulováno.")

    hraci[hrac].append(hodnota)
    score[hrac] = sum(hraci[hrac])

def to_sorted_tuple(d: dict[str, int], s: bool = True) -> tuple[list[tuple[int, str, int]],
                                                                dict[str, int]]:
    L: list[tuple[int, str, int]] = []

    if s:
        d = dict(sorted(d.items(), key=lambda x: x[1], reverse=True)) 

    for i, (k, v) in enumerate(d.items()):
        L.append((i+1, k, v))

    return L, d

def check_win() -> str:
    over_limit: dict[str, int] = {}
    for p in score:
        if score[p] >= final_score:
            over_limit[p] = score[p]

    winner: str = ""

    if over_limit:
        L, d = to_sorted_tuple(over_limit)

        count: Counter = Counter(list(d.values()))

        for c in count:
            if count[c] == 1:
                winner = L[0][1]
            break

    return winner

def win(winner: str, vitezne_skore: int) -> None:
    results, d = to_sorted_tuple(score)

    headers = ["Pořadí", "Hráč", "Skóre"]
    vysledky = tabulate(results, headers=headers, tablefmt="fancy_grid")

    print(f"Vítězem se stává {winner} s {vitezne_skore} body!")
    print("Díky za hru a zase příště.\n")

    print(vysledky)

def game():
    while True:
        clear()
        print(table())

        strikes: str = ""

        if len(hraci[pointer]) > 0:
            if hraci[pointer][-1] == 0:
                strikes = "x"
                if len(hraci[pointer]) > 1 and hraci[pointer][-2] == 0:
                    strikes += "x"
        else:
            strikes = ""

        inp = input(f"Zadejte skóre hráče {pointer} ({score[pointer]}{strikes}/{final_score}): ")
        try:
            inp_int = int(inp)
        except ValueError:
            clear()
            input("Zadejte prosím platnou číselnou hodnotu.")
            continue

        add_score(pointer, inp_int)
        next_player()

        if pointer == first:
            winner: str = check_win()
            if winner:
                clear()
                win(winner, score[winner])
                break


def main() -> None:
    clear()
    if char_create():
        clear()
        print("Vytvoření hráči:", ", ".join(list(hraci.keys())))
    else:
        print("Nastala chyba při vytváření uživatelů.")
        sys.exit()

    input("Stiskněte libovolnou klávesu pro pokračování. ")

    game()



if __name__ == "__main__":
    main()
