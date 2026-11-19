# =====================================================================
# cb_lod_minibus.py — Corsa Bis · LOD del minibus
# Cosa fa: mette in fila, sotto il tutorial, le sei versioni del minibus:
#   LOD0  modello completo (fase 8)                     a bordo, a piedi
#   LOD1  senza sedili e nastro, ruote a 2 dischi       zoom, modellino
#   LOD2  senza pezzi nascosti, ruote a 1 disco         volo d'uccello
#   LOD3  volumi principali, una sola mesh              tabellone vicino
#   LOD4  sagoma estrusa col cofano, finestrini e luci
#         dipinti                                       tabellone lontano
#   LOD5  gettone: tetto crema, cofano arancio e
#         parabrezza scuro davanti                      2D dall'alto
# Come: LOD1-3 e fila di confronto da cb_lod.py; qui LOD4 e LOD5.
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

_nome_main = __name__; __name__ = 'cb_extra'        # carica il minibus senza lanciarne il tutorial
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'run_tutorial' not in globals(): exec(_carica('cb_tutorial.py'))
exec(_carica('cb_minibus.py'))
exec(_carica('cb_lod.py'))
__name__ = _nome_main

def lod4(MAT, coll, loc):
    A, C, G, I = MAT['vernice_arancio'], MAT['vernice_crema'], MAT['vernice_grigio'], MAT['inchiostro']
    arco = lambda cx: [(cx - 0.62, ZB), (cx - 0.45, ZB + 0.42), (cx + 0.45, ZB + 0.42), (cx + 0.62, ZB)]
    corpo = [(XR, ZB)] + arco(WR) + arco(WF) + [(XF, ZB), (XF, ZH), (2.62, ZH), (2.42, ZT), (XR, ZT)]
    g = [([A, A, A], [estruso(corpo, -W, W)]),
         ([C, C, C], [lastra(-3.72, 2.55, -W, W, ZT, 0.06)]),
         ([G, G, G], [estruso(rect(-3.75, 0.42, 3.75, 0.72), -W, W)]),
         ruote_ottagono(MAT, (WR, WF), RW, ZA, W)]
    e = 0.006; vetri = []
    for s in (-1, 1):
        y = s*(W + e); vetri.append((quad((-3.42, y, 1.58), (2.12, y, 1.58), (2.12, y, 2.55), (-3.42, y, 2.55)), Matrix()))
    A0 = Vector((2.62 + e, 0, ZH)); B0 = Vector((2.42 + e, 0, ZT))
    vetri.append((quad((A0.x, -0.92, ZH + 0.22), (A0.x, 0.92, ZH + 0.22), (B0.x + 0.03, 0.92, ZT - 0.15), (B0.x + 0.03, -0.92, ZT - 0.15)), Matrix()))
    vetri.append((quad((XR - e, 0.8, 1.85), (XR - e, -0.8, 1.85), (XR - e, -0.8, 2.55), (XR - e, 0.8, 2.55)), Matrix()))
    vetri.append((quad((XF + e, -0.45, 0.85), (XF + e, 0.45, 0.85), (XF + e, 0.45, 1.30), (XF + e, -0.45, 1.30)), Matrix()))
    g.append(([I, I, I], vetri))
    xf = XF + e; xr = XR - e
    g.append(([MAT['luce_giallo']]*3, [(quad((xf, s*0.66, 1.03), (xf, s*0.90, 1.03), (xf, s*0.90, 1.27), (xf, s*0.66, 1.27)), Matrix()) for s in (-1, 1)]))
    g.append(([MAT['luce_rosso']]*3, [(quad((xr, s*0.92, 0.88), (xr, s*0.72, 0.88), (xr, s*0.72, 1.08), (xr, s*0.92, 1.08)), Matrix()) for s in (-1, 1)]))
    return [unisci('L4_Mezzo', g, coll, loc)]

def lod5(MAT, coll, loc):
    strati = [(MAT['vernice_arancio'], [rettangolo_a(XR, XF - 0.20, -1.05, 1.05)]),
              (MAT['vernice_crema'], [rettangolo_a(XR + 0.20, 2.10, -0.85, 0.85)]),
              (MAT['vernice_grigio'], [rettangolo_a(2.20, 2.60, -0.90, 0.90)])]
    return [unisci('L5_Gettone', gettone(MAT, -3.75, 3.75, 1.15, strati, punta=0.45, r=0.3), coll, loc)]

def run():
    if bpy.data.collections.get('Fase_8_Finito') is None:
        run_tutorial(CFG, pieces())
    return fila_lod('Minibus_LOD', CFG, pieces(), lod4, lod5, -30.0, 22.0, 11.0)

if __name__ == '__main__':
    print(run())
