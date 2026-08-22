# Počitadlo kostek jako kontejner.
#
# Staví se ze zdrojáků, ne z vydané binárky: image jde pak sestavit pro
# amd64 i arm64 a nezávisí na tom, jestli pro danou architekturu release
# proběhl. Závislosti jsou zamčené v requirements.txt, takže je sestavení
# opakovatelné.
#
#     docker build -f deploy/Dockerfile -t kostky .
#
# Sestavuje se z kořene repozitáře, ne z deploy/.
FROM python:3.11-slim

# Verze se jinak nemá kde vzít — v image není git ani zabalená binárka.
ARG VERSION=neznámá

RUN useradd --system --uid 1000 --home-dir /app --shell /usr/sbin/nologin kostky

WORKDIR /app

# Závislosti zvlášť a dřív než kód, ať se vrstva s pipem přestavuje jen tehdy,
# když se opravdu změnily.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY console.py core.py net.py stats.py storage.py version.py web.py ./
COPY templates/ templates/
COPY static/ static/
RUN echo "$VERSION" > verze.txt

# Adresář pro databázi musí vzniknout už tady a patřit správnému uživateli —
# svazek, který Docker založí sám, by jinak patřil rootovi a appka běžící pod
# kostky by do něj nezapsala.
RUN install -d -o kostky -g kostky /data
VOLUME ["/data"]

ENV DICE_DB=/data/dice.db \
    DICE_PORT=8000

EXPOSE 8000
USER kostky

# Bez curlu, ten ve slim image není. Stačí, že stránka odpoví — sahá i do
# databáze, takže se tím kontroluje i ta.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('DICE_PORT','8000') + '/')"

CMD ["python", "web.py"]
