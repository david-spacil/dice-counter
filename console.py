"""Aby výstup prošel i tam, kde ho nikdo nečeká na konzoli."""

import sys


def utf8() -> None:
    """Přepne standardní výstup na UTF-8 a na řádkové bufferování.

    Windows sahá po historické kódové stránce (cp1252, cp852) všude, kde
    výstup není konzole — přesměrovaný do souboru, puštěný ze skriptu, ve
    frontě CI. První háček nad takovým proudem shodí celý program, takže
    binárka umřela dřív, než stihla vypsat adresu, na které poslouchá.

    Na konzoli i na ostatních systémech je UTF-8 dávno výchozí a tohle je
    tam prázdná operace. `errors="replace"` je pojistka pro zbylé případy:
    rozsypaný háček je pořád lepší než spadlý server.

    Řádkové bufferování řeší druhou půlku téhož problému. Mimo konzoli
    Python drží výstup v bloku a pouští ho, až se naplní nebo až program
    skončí — jenže server neskončí, ten běží. Kdo si ho pustí na pozadí
    s výpisem do souboru, našel by tam prázdno; přesně to dělá zkouška
    binárky v CI. Pár řádek hlášky za to bufferovat nemá cenu.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace",
                               line_buffering=True)
