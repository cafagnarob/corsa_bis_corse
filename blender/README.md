# Blender — Corsa Bis

Modelli di mezzi e tessere generati da script Python.

## Cartelle

- `scripts/` — script `cb_*.py`. Si aprono nel Text Editor di Blender e si
  lanciano con _Run Script_, anche in un file vuoto: ogni script carica da solo
  gli altri dalla stessa cartella.
- `data/` — dati esportati per il gioco (`tessere_basi.json`: connettori e
  strade delle basi B01-B04).
- `files/` — file `.blend` di lavoro (tutorial di montaggio compreso). **Non sono
  nella repo**: si rigenerano dagli script; copia di sicurezza fuori da Git.

## Convenzioni

- Mezzi in metri reali; la scala di gioco la applica il codice.
- Tessere in unità di gioco: raggio 200, faccia superiore a Z = 0.
- Lati numerati: 0 = est, poi in senso antiorario.
