# Dice Counter

Doprovod k fyzickým kostkám: **telefon zapisuje skóre, notebook ukazuje
zápisník** a hry se pamatují mezi večery.

Hráči se napříč hrami poznávají podle jména — Adam ze středečního večera je
ten samý Adam jako z minulého měsíce. Žádné účty, žádná hesla.

## Spuštění

Stáhni binárku pro svůj systém z
[releases](https://gitea.spacilovi.eu/david-spacil/dice-counter/releases):

| Systém | Soubor |
|---|---|
| Linux (x86-64) | `kostky-linux-x86_64` |
| macOS (Apple Silicon) | `kostky-macos-arm64` |
| macOS (Intel) | `kostky-macos-x86_64` |
| Windows (x86-64) | `kostky-windows-x86_64.exe` |

Nic se neinstaluje — Python, Flask i šablony jsou uvnitř.

Na Linuxu a macOS:

```bash
chmod +x kostky-*
./kostky-linux-x86_64
```

Na Windows stačí na `.exe` poklepat.

Linuxová binárka je postavená proti glibc 2.17, takže jede prakticky všude.

### Než to poprvé pustíš

Binárky nejsou podepsané — podpisové certifikáty stojí tisíce ročně a na
počitadlo kostek by to byl nesmysl. Systémy si toho všimnou:

- **macOS** stažený soubor označí za karanténní a odmítne ho spustit. Buď
  značku sundej (`xattr -dr com.apple.quarantine kostky-macos-arm64`), nebo
  soubor stáhni rovnou z terminálu přes `curl -LO` — tudy se karanténa
  nenastavuje.
- **Windows** ukáže modré okno SmartScreenu. *Další informace* →
  *Přesto spustit*. Občas si postěžuje i antivirus; u zabalených Python
  programů je to běžný falešný poplach. Při prvním spuštění se ještě zeptá
  brána firewall — bez povolení do místní sítě se telefon nepřipojí.

Kdo tomu nechce věřit, ověří si stažený soubor podle přiloženého součtu
(níž) nebo si ho postaví sám — `./build.sh`, zdrojáky jsou tady celé.

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
nabízí i zbylé adresy — když jedna nefunguje, klikni na jinou a QR kód se
přepne na ni. Zastavuje se `Ctrl+C`.

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
| binárkou na Linuxu | `~/.local/share/kostky/dice.db` |
| binárkou na macOS | `~/Library/Application Support/kostky/dice.db` |
| binárkou na Windows | `%LOCALAPPDATA%\kostky\dice.db` |
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
| `.gitea/workflows/` | testy a linuxová binárka doma |
| `.github/workflows/` | binárky pro Windows a macOS |

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
potřeba není. Výsledek je v `dist/`.

Stejný `build.sh` staví i na macOS a na Windows (v Git Bash) — jen tam bez
té starosti o glibc. Křížem to nejde: PyInstaller balí do výsledku interpret
a knihovny toho systému, na kterém běží, takže **binárku pro každý systém
musí postavit ten systém.**

Terminálová verze součástí binárky není; ta se pouští ze zdrojáků.

### Jak vznikají releasy

Otagovaný commit spustí stavbu na obou stranách:

| Kde | Co staví | Workflow |
|---|---|---|
| vlastní runner u Gitey | Linux | `.gitea/workflows/binarka.yml` |
| GitHub Actions | Windows, macOS ×2 | `.github/workflows/binarky.yml` |

```bash
git tag v1.0.0 && git push origin v1.0.0
```

GitHub je tu jen půjčená dílna. Repozitář se tam z Gitey zrcadlí
([mirror](https://github.com/david-spacil/dice-counter)), postavené soubory
se posílají zpátky na zdejší release přes Gitea API a projekt má pořád jednu
stránku s releasy — tuhle. Linux se na GitHubu schválně nestaví; doma to jde
proti staré glibc, a když GitHub vypadne, release má aspoň tu platformu,
na které to reálně poběží.

Každá stavba nejdřív projede testy a zkusí hotovou binárku nastartovat, než
ji kamkoli pověsí. Vedle každé visí i `.sha256`, takže se stažený soubor dá
ověřit:

```bash
sha256sum -c kostky-linux-x86_64.sha256     # na macOS: shasum -a 256 -c
```

Nad pull requesty se Linux staví taky, jen se nikam nevěší.

## Testy

```bash
uv run --with-requirements requirements.txt --no-project pytest
```

Nebo z připraveného prostředí prostě `pytest`.

Nad každým pull requestem a nad `main` běží `.gitea/workflows/testy.yml` —
99 testů na Pythonu 3.11, 3.12, 3.13 i 3.14, a k tomu skriptovaná partie
v terminálové verzi, na kterou pytest nesahá.
