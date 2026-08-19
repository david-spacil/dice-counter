import sys
from os import name, system

from tabulate import tabulate

hraci = {}
score = {}
pointer = ""
first = ""

def clear() -> None:
    _ = system('cls') if name == 'nt' else system('clear') 

def char_create() -> bool:
    global pointer
    global first
    
    while True:
        inp: str = input("Zadejte jméno prvního hráče: ")
        if inp:
            hraci[inp] = []
            score[inp] = 0
            pointer = inp
            first = inp
            print(f"Hráč/ka {inp} přidán(a).")
            break
        else:
            print("Jméno nesmí být prázdné.")

    while True:
        inp = input("Zadejte jméno dalšího hráče (nebo nechte prázdné pro ukončení zadávání): ")
        if inp:
            if inp in hraci:
                print("Je potřeba zadávat unikátní jména.")
            else:
                hraci[inp] = []
                score[inp] = 0
                print(f"Hráč/ka {inp} přidán(a).")
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
    hraci[hrac].append(hodnota)
    score[hrac] += hodnota

def game():
    while True:
        clear()
        print(table())
        inp = input(f"Zadejte skóre hráče {pointer}: ")
        inp_int = int(inp)
        add_score(pointer, inp_int)
        next_player()
        # break
    

def main() -> None:
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
