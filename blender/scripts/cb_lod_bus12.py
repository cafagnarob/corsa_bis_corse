# =====================================================================
# cb_lod_bus12.py — Corsa Bis · LOD del bus urbano 12 m
# Cosa fa: mette in fila, sotto il tutorial, le sei versioni del bus:
#   LOD0  modello completo (fase 9)                     a bordo, a piedi
#   LOD1  senza interni, ruote a 2 dischi               zoom, modellino
#   LOD2  senza pezzi nascosti, ruote a 1 disco         volo d'uccello
#   LOD3  volumi principali, una sola mesh              tabellone vicino
#   LOD4  scatola estrusa: fascia dei finestrini dipinta,
#         climatizzatore, luci                          tabellone lontano
#   LOD5  gettone visto dall'alto: tetto crema, bordo arancio,
#         climatizzatore, parabrezza scuro sul muso     2D dall'alto
# Come: LOD1-3 e fila di confronto da cb_lod.py; qui LOD4 e LOD5 disegnati
#   sulla forma del bus. Misure del GDD in metri reali.
# Uso: apri il file nel Text Editor e premi Run Script.
# =====================================================================
import bpy, math, os
from mathutils import Vector, Matrix

def _carica(nome):
    t = bpy.data.texts.get(nome)
    if t is not None: return t.as_string()
    for tx in bpy.data.texts:
        if tx.filepath:
            p = os.path.join(os.path.dirname(bpy.path.abspath(tx.filepath)), nome)
            if os.path.exists(p):
                with open(p, encoding='utf-8') as f: return f.read()
    raise FileNotFoundError(nome + ': aprilo nel Text Editor o mettilo nella stessa cartella di questo script')

_nome_main = __name__; __name__ = 'cb_lod'          # carica il bus senza lanciarne il tutorial
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'run_tutorial' not in globals(): exec(_carica('cb_tutorial.py'))
exec(_carica('cb_bus12.py'))
exec(_carica('cb_lod.py'))
__name__ = _nome_main

def lod4(MAT, coll, loc):
    A, C, G, I = MAT['vernice_arancio'], MAT['vernice_crema'], MAT['vernice_grigio'], MAT['inchiostro']
    arco = lambda cx: [(cx - 0.62, ZB), (cx - 0.45, ZB + 0.42), (cx + 0.45, ZB + 0.42), (cx + 0.62, ZB)]
    corpo = [(XR, ZB)] + arco(WR) + arco(WF) + [(XF, ZB), (XF, ZM), (XF - SLANT, ZT), (XR, ZT)]
    g = [([A, A, A], [estruso(corpo, -W, W)]),
         ([C, C, C], [lastra(XR - 0.04, XF - SLANT + 0.04, -W, W, ZT, 0.06), lastra(-1.6, 0.6, -0.75, 0.75, ZT + 0.06, 0.22)]),
         ruote_ottagono(MAT, (WR, WF), RW, ZA, W)]
    e = 0.006; vetri = []
    for s in (-1, 1):
        y = s*(W + e); vetri.append((quad((-5.7, y, ZW0), (3.95, y, ZW0), (3.95, y, ZW1), (-5.7, y, ZW1)), Matrix()))
    yd = -(W + e)
    for d in (DOOR_F, DOOR_M): vetri.append((quad((d[0], yd, 0.62), (d[1], yd, 0.62), (d[1], yd, ZW1), (d[0], yd, ZW1)), Matrix()))
    x0 = XF + e; x1 = XF - SLANT + e
    vetri.append((quad((x0, -1.08, ZM + 0.10), (x0, 1.08, ZM + 0.10), (x1, 1.08, ZT - 0.12), (x1, -1.08, ZT - 0.12)), Matrix()))
    vetri.append((quad((XR - e, 0.95, 1.90), (XR - e, -0.95, 1.90), (XR - e, -0.95, ZW1), (XR - e, 0.95, ZW1)), Matrix()))
    g.append(([I, I, I], vetri))
    xf = XF + e + 0.02; xr = XR - e
    g.append(([MAT['luce_giallo']]*3, [(quad((xf, s*0.75, 0.82), (xf, s*1.08, 0.82), (xf, s*1.08, 1.02), (xf, s*0.75, 1.02)), Matrix()) for s in (-1, 1)]))
    g.append(([MAT['luce_rosso']]*3, [(quad((xr, s*1.08, 0.90), (xr, s*0.85, 0.90), (xr, s*0.85, 1.10), (xr, s*1.08, 1.10)), Matrix()) for s in (-1, 1)]))
    return [unisci('L4_Mezzo', g, coll, loc)]

def lod5(MAT, coll, loc):
    w = 1.30
    strati = [(MAT['vernice_arancio'], [rettangolo_a(XR, XF - 0.30, -1.18, 1.18)]),
              (MAT['vernice_crema'], [rettangolo_a(XR + 0.25, XF - 1.30, -0.95, 0.95)]),
              # parabrezza scuro largo e muso arancio: il verso di marcia si legge anche senza la punta
              (MAT['vernice_grigio'], [rettangolo_a(-1.6, 0.6, -0.6, 0.6), rettangolo_a(XF - 1.15, XF - 0.55, -1.0, 1.0)])]
    return [unisci('L5_Gettone', gettone(MAT, -6.0, 6.0, w, strati), coll, loc)]

def scritta(L, coll, MAT, loc):
    # la scritta della linea resta nei LOD vicini
    scritta_linea(CFG['final_stage'], coll, MAT, tuple(loc))

def run():
    if bpy.data.collections.get('Fase_9_Finito') is None:
        run_tutorial(CFG, pieces(), scritta_linea)
    return fila_lod('Bus12_LOD', CFG, pieces(), lod4, lod5, -30.0, 36.0, 16.0, scritta)

if __name__ == '__main__':
    print(run())
