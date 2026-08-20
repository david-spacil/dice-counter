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

Server vypíše všechny adresy, na kterých je dostupný:

```
Počitadlo je dostupné na:
 → http://10.186.234.182:8000     místní síť
   http://100.91.0.24:8000        přes Tailscale
   http://172.17.0.1:8000         virtuální síť
```

Na notebooku otevři `/board`, naskenuj QR kód telefonem a hraj. Tabule
zobrazuje i zbylé adresy — když jedna nefunguje, zkus další.

| Proměnná | K čemu je | Výchozí |
|---|---|---|
| `DICE_DB` | soubor s databází | `dice.db` |
| `DICE_PORT` | port | `8000` |
| `DICE_HOST` | pevná adresa; vypne hledání | hledá se za běhu |

Počítá se s domácí sítí — appka nemá přihlašování a kdokoli na stejné WiFi
může zapisovat.

## Když se telefon nepřipojí

Adresy se hledají při každém načtení tabule, takže přechod z domácí WiFi na
hotspot a zpátky si tabule pohlídá sama a načte se znovu.

Zbývají tři důvody, proč se telefon nedostane na notebook:

- **Telefon je na mobilních datech**, notebook na WiFi. Různé sítě, nepotkají
  se. Připoj telefon na stejnou WiFi, nebo notebook na hotspot telefonu —
  to funguje taky.
- **Zapnutý hotspot na telefonu shodil jeho WiFi.** Většina Androidů to dělá.
  Pak je řešením připojit na ten hotspot i notebook.
- **VPN nebo Tailscale exit node na telefonu** posílá veškerý provoz mimo
  místní síť. V Tailscale to řeší přepínač „Allow local network access";
  případně použij tailnet adresu notebooku, ta funguje odkudkoli.

## Pravidla

Skóre se zadává ručně po tazích, hází se doopravdy. Tři nulové tahy za sebou
vynulují hráči skóre; indikátor `x` / `xx` ukazuje, jak blízko k tomu je.
Vítěz se vyhlašuje až po dokončeném kole, aby měli všichni stejný počet tahů —
při remíze na prvním místě se hraje dál.

## Co kde je

| Soubor | Role |
|---|---|
| `core.py` | pravidla hry, žádný vstup ani výstup |
| `net.py` | hledání adres, na kterých je počitadlo dostupné |
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
