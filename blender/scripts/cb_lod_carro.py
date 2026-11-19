# =====================================================================
# cb_lod_carro.py — Corsa Bis · LOD del carro attrezzi
# Cosa fa: mette in fila, sotto il tutorial, le sei versioni del carro
#   attrezzi, ognuna con un cartellino (vista del GDD + triangoli):
#   LOD0  il modello completo (fase 9)        a bordo, a piedi
#   LOD1  senza interni, ruote a 2 dischi      zoom e modellino sul tavolo
#   LOD2  senza pezzi nascosti, ruote a 1 disco volo d'uccello
#   LOD3  volumi principali, una sola mesh     3D tabellone, tessere vicine
#   LOD4  sagome estruse a blocchi             3D tabellone, tessere lontane
#   LOD5  gettone di cartone visto dall'alto   2D dall'alto (icona)
# Come: LOD1-3 vengono da cb_lod.py (regole uguali per tutti i mezzi);
#   LOD4 e LOD5 sono disegnati qui con la forma del carro. Le misure sono
#   sempre quelle del GDD in metri reali: la scala di gioco la applica il codice.
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

_nome_main = __name__; __name__ = 'cb_lod'          # carica il carro senza lanciarne il tutorial
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'run_tutorial' not in globals(): exec(_carica('cb_tutorial.py'))
exec(_carica('cb_carro_attrezzi.py'))
exec(_carica('cb_lod.py'))
__name__ = _nome_main

ROOT = 'CarroAttrezzi_LOD'
RIGA_Y, X0, PASSO = -29.0, 30.0, 12.0
VISTE = {0: 'a bordo, a piedi', 1: 'zoom e modellino sul tavolo', 2: "volo d'uccello",
         3: '3D tabellone vicino', 4: '3D tabellone lontano', 5: '2D dall\'alto'}

# ---------- pezzi semplici ----------
def quad(p0, p1, p2, p3):
    # un rettangolo senza spessore (2 triangoli): finestrini, luci, strati del gettone
    return ([tuple(p0), tuple(p1), tuple(p2), tuple(p3)], [(0, 1, 2, 3)], [0], [[(0, 0), (1, 0), (1, 1), (0, 1)]], [])

def estruso(profilo, y0, y1, **kw):
    # profilo nel piano x-z estruso lungo y: un volume a blocchi senza bordi storti
    g = build_panel(profilo, t=y1 - y0, rough=0.0, warp=0.0, nick=0.0, step=50.0, **kw)
    return g, frame((0, y0, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0))

def disco_piatto(cx, cy, r, z, n=6):
    V = [(cx, cy, z)] + [(cx + r*math.cos(2*math.pi*i/n), cy + r*math.sin(2*math.pi*i/n), z) for i in range(n)]
    F = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    return (V, F, [0]*n, [[(0, 0), (1, 0), (1, 1)]]*n, [])

def unisci(nome, gruppi, coll, loc):
    # gruppi: lista di (materiali [faccia, bordo, retro], [(geo, matrice), ...]) -> un solo oggetto
    slots = []; geos = []
    for mats, items in gruppi:
        idx = []
        for m in mats:
            if m not in slots: slots.append(m)
            idx.append(slots.index(m))
        for (V, F, M_, U, S), Mx in items:
            geos.append(((V, F, [idx[m] for m in M_], U, S), Mx))
    return make_object(nome, geos, slots, coll, loc)

# ---------- LOD4: sagome estruse ----------
def lod4(MAT, coll, loc):
    A = MAT['vernice_arancio']; G = MAT['vernice_grigio']; C = MAT['vernice_crema']
    K = MAT['kraft']; B = MAT['bordo']; I = MAT['inchiostro']
    arco = lambda cx: [(cx - 0.62, ZB), (cx - 0.45, ZB + 0.42), (cx + 0.45, ZB + 0.42), (cx + 0.62, ZB)]
    cab = [(XC, ZB)] + arco(WF) + [(XF, ZB), (XF, ZH), (XH, ZH), (XH - 0.15, ZT), (XC, ZT)]
    cas = [(XB, ZB)] + arco(WR) + [(XC, ZB), (XC, ZS), (XB, ZS)]
    tower = [(-0.30, ZP), (1.35, ZP), (1.35, 1.20), (1.00, 2.55), (0.55, 2.55)]
    d = (P1 - P0).normalized(); p0e = P0 - d*0.25
    g = []
    g.append(([A, A, A], [estruso(cab, -W, W), estruso(tower, -0.3, 0.3), estruso(beam(p0e, P1, HB), -0.18, 0.18)]))
    g.append(([G, G, G], [estruso(cas, -W, W)]))
    g.append(([C, C, C], [(build_panel(rect(XC - 0.05, -W, XH - 0.09, W), t=0.06, rough=0, warp=0, nick=0, step=50), frame((0, 0, ZT), (1, 0, 0), (0, 1, 0)))]))
    ruote = []
    for cx in (WR, WF):
        for s in (-1, 1):
            y0, y1 = sorted((s*(W - 0.30), s*(W + 0.02)))
            ruote.append((build_panel(circle(0, 0, RW, 8, math.pi/8), t=y1 - y0, rough=0, warp=0, nick=0, step=50), frame((cx, y0, ZA), (1, 0, 0), (0, 0, 1), (0, 1, 0))))
    g.append(([K, B, K], ruote))
    e = 0.006; vetri = []
    for s in (-1, 1):
        y = s*(W + e); vetri.append((quad((1.75, y, 1.85), (2.56, y, 1.85), (2.56, y, 2.65), (1.75, y, 2.65)), Matrix()))
    x0 = XH + e; x1 = XH - 0.15 + e
    vetri.append((quad((x0, -1.05, ZH + 0.12), (x0, 1.05, ZH + 0.12), (x1, 1.05, ZT - 0.12), (x1, -1.05, ZT - 0.12)), Matrix()))
    g.append(([I, I, I], vetri))
    xf = XF + e; xr = XB - e; zl = ZT + 0.065
    g.append(([MAT['luce_giallo']]*3, [(quad((xf, s*0.75, 0.92), (xf, s*1.02, 0.92), (xf, s*1.02, 1.18), (xf, s*0.75, 1.18)), Matrix()) for s in (-1, 1)]))
    g.append(([MAT['luce_rosso']]*3, [(quad((xr, s*1.0, 0.85), (xr, s*0.78, 0.85), (xr, s*0.78, 1.05), (xr, s*1.0, 1.05)), Matrix()) for s in (-1, 1)]))
    g.append(([MAT['luce_arancio']]*3, [(disco_piatto(2.4, s*0.6, 0.14, zl, 5), Matrix()) for s in (-1, 1)]))
    return [unisci('L4_Mezzo', g, coll, loc)]

# ---------- LOD5: gettone 2D ----------
def lod5(MAT, coll, loc):
    # gettone di cartone con la sagoma vista dall'alto: punta a freccia sul muso
    # per leggere il verso di marcia nella vista 2D, colori della livrea sopra
    xr, xf, w = -4.25, 4.25, 1.32; r = 0.35
    out = arc(xr + r, -w + r, r, math.pi, 1.5*math.pi, 3) + [(xf - 0.55, -w), (xf, 0.0), (xf - 0.55, w)] + arc(xr + r, w - r, r, 0.5*math.pi, math.pi, 3)
    zt = 0.15; e = 0.004
    chip = build_panel(out, t=zt, rough=0.0, warp=0.0, nick=0.0, step=50.0)
    def strato(x0, x1, y0, y1, z): return (quad((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)), Matrix())
    z1 = zt + e; z2 = zt + 2*e
    g = [([MAT['kraft'], MAT['bordo'], MAT['interno']], [(chip, Matrix())]),
         ([MAT['vernice_grigio']]*3, [strato(XB, XC, -1.1, 1.1, z1)]),
         ([MAT['vernice_arancio']]*3, [strato(XH, XF - 0.25, -1.1, 1.1, z1)]),
         ([MAT['vernice_crema']]*3, [strato(XC, XH, -1.1, 1.1, z1), strato(P1.x + 0.05, P0.x, -0.18, 0.18, z2)]),
         ([MAT['luce_arancio']]*3, [(disco_piatto(2.4, s*0.6, 0.16, z2, 5), Matrix()) for s in (-1, 1)])]
    return [unisci('L5_Gettone', g, coll, loc)]

# ---------- fila di confronto ----------
def run():
    MAT = make_materials()
    root = reset_coll(ROOT)
    src = bpy.data.collections.get('Fase_9_Finito')
    if src is None:
        run_tutorial(CFG, pieces()); src = bpy.data.collections['Fase_9_Finito']
    PCS = pieces(); conteggi = {}
    for L in range(6):
        c = reset_coll(f'LOD{L}', root); loc = (X0 + L*PASSO, RIGA_Y, 0.0)
        if L == 0:
            objs = []
            for o in src.objects:
                if o.type == 'MESH' and o.name.startswith('F9_'):
                    n = o.copy(); n.name = 'L0_' + o.name[3:]; n.location = loc; c.objects.link(n); objs.append(n)
        elif L <= 3:
            objs = costruisci(pezzi_lod(PCS, CFG, L), MAT, CFG, c, loc, f'L{L}', unisci=(L == 3))
        elif L == 4:
            objs = lod4(MAT, c, loc)
        else:
            objs = lod5(MAT, c, loc)
        n = triangoli(objs); conteggi[L] = (n, len(objs))
        cartellino(f'LOD{L} · {VISTE[L]} · {n:,} tri'.replace(',', '.'), (loc[0], RIGA_Y - CFG['label_dy'], 0.0), c, MAT)
    return conteggi

if __name__ == '__main__':
    print(run())
