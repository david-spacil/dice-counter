import sys
from os import name, system

hraci = {}

def clear() -> None:
    _ = system('cls') if name == 'nt' else system('clear') 

def char_create() -> bool:
    global hraci
    
    while True:
        inp: str = input("Zadejte jméno prvního hráče: ")
        if inp:
            hraci[inp] = 0
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
                hraci[inp] = 0
                print(f"Hráč/ka {inp} přidán(a).")
        else:
            break

    return True

def game():
    while True:
        table()
    

def main() -> None:
    if char_create():
        clear()
        print("Vytvoření hráči:", ", ".join(list(hraci.keys())))
    else:
        print("Nastala chyba při vytváření uživatelů.")
        sys.exit()
    input("Stiskněte libovolnou klávesu pro pokračování. ")

    

if __name__ == "__main__":
    main()
