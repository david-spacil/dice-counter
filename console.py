"""Aby čeština prošla i tam, kde konzole čeká něco jiného."""

import sys


def utf8() -> None:
    """Přepne standardní výstup na UTF-8.

    Windows sahá po historické kódové stránce (cp1252, cp852) všude, kde
    výstup není konzole — přesměrovaný do souboru, puštěný ze skriptu, ve
    frontě CI. První háček nad takovým proudem shodí celý program, takže
    binárka umřela dřív, než stihla vypsat adresu, na které poslouchá.

    Na konzoli i na ostatních systémech je UTF-8 dávno výchozí a tohle je
    tam prázdná operace. `errors="replace"` je pojistka pro zbylé případy:
    rozsypaný háček je pořád lepší než spadlý server.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
