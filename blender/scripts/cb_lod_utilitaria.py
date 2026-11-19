# =====================================================================
# cb_lod_utilitaria.py — Corsa Bis · LOD dell'utilitaria
# Cosa fa: mette in fila, sotto il tutorial, le sei versioni dell'auto:
#   LOD0  modello completo (fase 8)                     a bordo, a piedi
#   LOD1  senza sedili, volante e nastro, ruote a 2 dischi  zoom, modellino
#   LOD2  senza pezzi nascosti, ruote a 1 disco         volo d'uccello
#   LOD3  volumi principali, una sola mesh              tabellone vicino
#   LOD4  sagoma estrusa, finestrini, luci e coprimozzi
#         rossi dipinti                                 tabellone lontano
#   LOD5  gettone: tetto, parabrezza e lunotto scuri,
#         cofano davanti                                2D dall'alto
# Come: LOD1-3 e fila di confronto da cb_lod.py; qui LOD4 e LOD5. Il colore
#   della carrozzeria segue CARROZZERIA di cb_utilitaria.py (None = kraft).
#   Le auto del traffico sono centinaia: nel gioco useranno quasi sempre
#   LOD3-5 con l'instancing.
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

_nome_main = __name__; __name__ = 'cb_extra'        # carica l'utilitaria senza lanciarne il tutorial
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'run_tutorial' not in globals(): exec(_carica('cb_tutorial.py'))
exec(_carica('cb_utilitaria.py'))
exec(_carica('cb_lod.py'))
__name__ = _nome_main

def corpo_mat(MAT):
    return MAT['vernice_' + CARROZZERIA] if CARROZZERIA else MAT['kraft']

def lod4(MAT, coll, loc):
    K = corpo_mat(MAT); I = MAT['inchiostro']; R = MAT['vernice_rosso']
    arco = lambda cx: [(cx - 0.38, ZB), (cx - 0.28, ZB + 0.26), (cx + 0.28, ZB + 0.26), (cx + 0.38, ZB)]
    corpo = [(XR, ZB)] + arco(WR) + arco(WF) + [(XF, ZB), (XF, ZH), (XA0, ZH), (XA1, ZT), (XP1, ZT), (XP0, ZL)]
    g = [([K, K, K], [estruso(corpo, -W, W),   # fianchi dell'estruso = tetto e cofano: niente onda
                                  estruso(rect(XR - 0.14, 0.26, XF + 0.14, 0.42), -W, W)]),
         ruote_ottagono(MAT, (WR, WF), RW, ZA, W, larg=0.20)]
    e = 0.006; vetri = []
    for s in (-1, 1):
        y = s*(W + e)
        for l in (FIN_ANT, FIN_POST, FIN_TERZO):
            if len(l) == 4: vetri.append((quad(*[(x, y, z) for x, z in l]), Matrix()))
    def sul_piano(A, B, w, m0, m1):
        A = Vector(A); B = Vector(B); d = (B - A).normalized(); L = (B - A).length
        p0 = A + d*m0; p1 = A + d*(L - m1)
        return quad((p0.x, -w, p0.z), (p0.x, w, p0.z), (p1.x, w, p1.z), (p1.x, -w, p1.z))
    vetri.append((sul_piano((XA0 + e, 0, ZH), (XA1 + e, 0, ZT), 0.62, 0.08, 0.08), Matrix()))
    vetri.append((sul_piano((XP0 - e, 0, ZL), (XP1 - e, 0, ZT), 0.55, 0.07, 0.08), Matrix()))
    vetri.append((quad((XF + e, -0.30, 0.50), (XF + e, 0.30, 0.50), (XF + e, 0.30, 0.76), (XF + e, -0.30, 0.76)), Matrix()))
    g.append(([I, I, I], vetri))
    yr = W + 0.025; hub = []
    for cx in (WR, WF):
        for s in (-1, 1):
            V = [(cx + 0.14*math.cos(2*math.pi*i/6), s*yr, ZA + 0.14*math.sin(2*math.pi*i/6)) for i in range(6)]
            hub.append(((V, [tuple(range(6)) if s > 0 else tuple(reversed(range(6)))], [0], [[(0, 0)]*6], []), Matrix()))
    g.append(([R, R, R], hub))
    xf = XF + e; xr = XR - e
    g.append(([MAT['luce_giallo']]*3, [(quad((xf, s*0.45, 0.53), (xf, s*0.65, 0.53), (xf, s*0.65, 0.73), (xf, s*0.45, 0.73)), Matrix()) for s in (-1, 1)]))
    g.append(([MAT['luce_rosso']]*3, [(quad((xr, s*0.66, 0.71), (xr, s*0.50, 0.71), (xr, s*0.50, 0.85), (xr, s*0.66, 0.85)), Matrix()) for s in (-1, 1)]))
    return [unisci('L4_Mezzo', g, coll, loc)]

def lod5(MAT, coll, loc):
    G = MAT['vernice_grigio']
    strati = [(G, [rettangolo_a(XA1 + 0.04, XA0 - 0.04, -0.62, 0.62), rettangolo_a(XP0 + 0.04, XP1 - 0.02, -0.55, 0.55)]),
              (MAT['vernice_rosso'], [rettangolo_a(cx - 0.14, cx + 0.14, s*0.80 - 0.04, s*0.80 + 0.04) for cx in (WR, WF) for s in (-1, 1)])]
    g = gettone(MAT, -1.80, 1.80, 0.85, strati, punta=0.28, r=0.22, zt=0.12)
    if CARROZZERIA:
        g.insert(1, ([corpo_mat(MAT)]*3, [(rettangolo_a(XR, XF, -0.78, 0.78)(0.124), Matrix())]))
    return [unisci('L5_Gettone', g, coll, loc)]

def run():
    if bpy.data.collections.get('Fase_8_Finito') is None:
        run_tutorial(CFG, pieces())
    return fila_lod('Utilitaria_LOD', CFG, pieces(), lod4, lod5, -32.0, 13.0, 11.0)   # passo largo: i cartellini non si sovrappongono

if __name__ == '__main__':
    print(run())
