# Počitadlo v kostkách

Doprovod k fyzickým kostkám: **telefon zapisuje skóre, notebook ukazuje
zápisník** a hry se pamatují mezi večery.

Hráči se napříč hrami poznávají podle jména — Adam ze středečního večera je
ten samý Adam jako z minulého měsíce. Žádné účty, žádná hesla.

## Spuštění

Stáhni binárku z [releases](https://gitea.spacilovi.eu/david-spacil/dice-counter/releases)
a spusť ji:

```bash
chmod +x kostky
./kostky
```

Nic se neinstaluje — Python, Flask i šablony jsou uvnitř. Zatím jen pro Linux
na x86-64; postavené proti glibc 2.17, takže jede prakticky všude.

Ze zdrojáků to je stejně krátké:

```bash
uv run web.py
```

Závislosti si skript nese v hlavičce (PEP 723) a `uv` je obstará sám.

Server vypíše všechny adresy, na kterých je dostupný:

```
Počitadlo je dostupné na:
 → http://10.186.234.182:8000     místní síť
   http://100.91.0.24:8000        přes Tailscale
   http://172.17.0.1:8000         virtuální síť
```

Na notebooku otevři `/board`, naskenuj QR kód telefonem a hraj. Tabule
zobrazuje i zbylé adresy — když jedna nefunguje, zkus další. Zastavuje se
`Ctrl+C`.

| Proměnná | K čemu je | Výchozí |
|---|---|---|
| `DICE_DB` | soubor s databází | podle způsobu spuštění, viz níž |
| `DICE_PORT` | port | `8000` |
| `DICE_HOST` | pevná adresa; vypne hledání | hledá se za běhu |

## Kde jsou data

Jeden soubor SQLite. Založí se sám při prvním načtení stránky, cestu k němu
server vypíše při startu.

| Spuštěno | Databáze |
|---|---|
| binárkou | `~/.local/share/kostky/dice.db` |
| ze zdrojáků | `dice.db` v pracovním adresáři |

Binárka se při každém spuštění rozbaluje do dočasného adresáře a pouští se
odkudkoli, takže relativní cesta by databázi rozsypala po disku — proto
napevno domovský adresář. Ze zdrojáků zůstává relativní, ať se dá mít víc
sad vedle sebe.

Zálohovat i stěhovat jde prostým zkopírováním souboru; `DICE_DB` si ho
najde kdekoli.

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
| `build.sh`, `kostky.spec` | stavba binárky |

Terminálová verze zůstává funkční jako záloha:

```bash
uv run dice.py
```

## Bez uv

Když `uv` po ruce není, jde to postaru:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python web.py
```

Na Fedoře stačí i systémové balíčky, pak se nemusí řešit vůbec nic:

```bash
sudo dnf install python3-flask python3-qrcode python3-tabulate
python3 web.py
```

## Vlastní binárka

```bash
./build.sh
```

Staví se proti samostatnému CPythonu od `uv`, ne proti systémovému. Ten je
slinkovaný s glibc 2.17; postavené proti Pythonu z Fedory 44 by to chtělo
glibc 2.43 a nešlo by spustit skoro nikde — glibc drží zpětnou kompatibilitu,
ne dopřednou. Nic z hostitele se do binárky nedostane, takže kontejner k tomu
potřeba není. Výsledek je v `dist/kostky`.

Terminálová verze součástí binárky není; ta se pouští ze zdrojáků.

Releasy si tohle dělají samy. Otagovaný commit spustí
`.gitea/workflows/binarka.yml`, ta binárku postaví, projede testy, zkusí
ji nastartovat a pověsí ji na release jako `kostky-linux-x86_64`:

```bash
git tag v1.0.0 && git push origin v1.0.0
```

Stejná stavba běží i nad každým pull requestem, jen se nikam nevěší.

## Testy

```bash
uv run --with-requirements requirements.txt --no-project pytest
```

Nebo z připraveného prostředí prostě `pytest`.

Nad každým pull requestem a nad `main` běží `.gitea/workflows/testy.yml` —
84 testů na Pythonu 3.11, 3.12, 3.13 i 3.14, a k tomu skriptovaná partie
v terminálové verzi, na kterou pytest nesahá.
