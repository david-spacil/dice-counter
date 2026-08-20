# Počitadlo v kostkách

Doprovod k fyzickým kostkám: **telefon zapisuje skóre, notebook ukazuje
zápisník** a hry se pamatují mezi večery.

Hráči se napříč hrami poznávají podle jména — Adam ze středečního večera je
ten samý Adam jako z minulého měsíce. Žádné účty, žádná hesla.

## Spuštění

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python web.py
```

Server vypíše adresu, na které poslouchá. Na notebooku otevři `/board`,
naskenuj QR kód telefonem a hraj.

| Proměnná | K čemu je | Výchozí |
|---|---|---|
| `DICE_DB` | soubor s databází | `dice.db` |
| `DICE_PORT` | port | `8000` |
| `DICE_HOST` | adresa v QR kódu, když ji nemá hledat sám | zjistí se za běhu |

Počítá se s domácí sítí — appka nemá přihlašování a kdokoli na stejné WiFi
může zapisovat.

## Pravidla

Skóre se zadává ručně po tazích, hází se doopravdy. Tři nulové tahy za sebou
vynulují hráči skóre; indikátor `x` / `xx` ukazuje, jak blízko k tomu je.
Vítěz se vyhlašuje až po dokončeném kole, aby měli všichni stejný počet tahů —
při remíze na prvním místě se hraje dál.

## Co kde je

| Soubor | Role |
|---|---|
| `core.py` | pravidla hry, žádný vstup ani výstup |
| `storage.py` | SQLite: hráči, hry, tahy |
| `stats.py` | síň slávy a kariérní statistiky |
| `web.py` | Flask aplikace |
| `dice.py` | totéž v terminálu, bez ukládání |

Terminálová verze zůstává funkční jako záloha:

```bash
.venv/bin/python dice.py
```

## Testy

```bash
.venv/bin/python -m pytest tests/ -v
```
