# =====================================================================
# cb_binari.py — Corsa Bis · Binari del tram in cartone
# Cosa fa: costruisce i pezzi di binario in fila, ognuno col suo cartellino:
#   Dritto        12 m
#   Curva         raggio 25 m, 30° (verso sinistra; ruotato di 180° fa la destra)
#   Scambio       dritto 12 m + deviata a destra (raggio 25 m, 26°), con la
#                 cassetta e leva di manovra
#   Bivio         biforcazione simmetrica a Y, ±15° (raggio 25 m)
#   Incrocio      due binari dritti che si tagliano a 90°
#   Tronchino     fine binario con il respingente (capolinea a tronchino del GDD)
# Come: ogni pezzo è una o più "tracce" (linee guida dritte o ad arco).
#   Lungo ogni traccia: sede di cartone kraft (larga 2,6 m), traverse di
#   legno (bastoncini) ogni 0,7 m, due rotaie di cartone grigio alte 12 cm.
#   Scartamento reale 1,435 m (metri reali come tutti i modelli; la scala di
#   gioco la applica il codice). Tutti i pezzi partono dall'origine verso +X,
#   così si agganciano in fila: la fine di un pezzo è l'inizio del successivo.
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

if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'run_tutorial' not in globals(): exec(_carica('cb_tutorial.py'))

SCART = 1.435; G = SCART/2                   # scartamento e mezzo scartamento
SEDE = 1.30; ZS = 0.05                       # mezza larghezza della sede, spessore
RR, ZR = 0.045, 0.12                         # mezza larghezza e altezza della rotaia
PASSO_T, TRAV = 0.7, 1.15                    # passo e mezza lunghezza delle traverse
R, L = 25.0, 12.0                            # raggio delle curve, lunghezza del dritto
ROOT = 'Binari'; RIGA_Y = -55.0                # sotto il tappetino del tutorial

# ---------- tracce: liste di (punto, direzione) campionate ----------
def dritto(lung, p0=(0, 0), ang=0.0, n=None):
    n = n or max(2, int(lung/1.0)); d = Vector((math.cos(ang), math.sin(ang)))
    return [(Vector(p0) + d*lung*i/n, ang) for i in range(n + 1)]

def curva(raggio, gradi, verso=1, p0=(0, 0), ang=0.0):
    # verso +1 = sinistra, -1 = destra
    a = math.radians(gradi); n = max(4, int(raggio*a/0.8)); p0 = Vector(p0)
    c = p0 + Vector((-math.sin(ang), math.cos(ang)))*raggio*verso
    out = []
    for i in range(n + 1):
        t = ang + verso*a*i/n
        out.append((c + Vector((math.sin(t), -math.cos(t)))*raggio*verso, t))
    return out

def nastro(tr, d0, d1):
    # contorno di una striscia parallela alla traccia, tra gli scostamenti d0 e d1
    sx = lambda p, a, d: tuple(p + Vector((-math.sin(a), math.cos(a)))*d)
    return [sx(p, a, d1) for p, a in tr] + [sx(p, a, d0) for p, a in reversed(tr)]

def lunghezza(tr):
    return sum((tr[i][0] - tr[i-1][0]).length for i in range(1, len(tr)))

def lungo(tr, s):
    # punto e direzione alla distanza s lungo la traccia
    acc = 0.0
    for i in range(1, len(tr)):
        seg = (tr[i][0] - tr[i-1][0]).length
        if acc + seg >= s:
            f = (s - acc)/seg if seg else 0
            return tr[i-1][0].lerp(tr[i][0], f), tr[i-1][1] + (tr[i][1] - tr[i-1][1])*f
        acc += seg
    return tr[-1]

# ---------- costruzione ----------
def binario(tracce, seed, salta_traverse=None):
    sedi, rotaie, trav = [], [], []
    for k, tr in enumerate(tracce):
        z0 = ZS*(1 + 0.04*k)                                  # sedi sovrapposte: niente sfarfallio
        sedi.append((build_panel(nastro(tr, -SEDE, SEDE), t=z0, rough=0.012, nick=0.03, warp=0.0, seed=seed + k), Matrix()))
        for j, g in enumerate((-G, G)):
            rotaie.append((build_panel(nastro(tr, g - RR, g + RR), t=ZR + 0.002*k, rough=0.003, nick=0.006, warp=0.0, step=0.3,
                                       seed=seed + 10*k + j), Matrix.Translation((0, 0, ZS + 0.04))))
        s = PASSO_T/2
        while s < lunghezza(tr):
            p, a = lungo(tr, s)
            if not (salta_traverse and salta_traverse(k, p)):
                d = Vector((-math.sin(a), math.cos(a)))
                g = build_panel(circle(0, 0, 0.022, 8), t=2*TRAV, rough=0.0, warp=0.0, nick=0.0)
                trav.append((g, frame_dir(Vector((*(p - d*TRAV), ZS + 0.022)), Vector((*d, 0)))))
            s += PASSO_T
    return sedi, rotaie, trav

def oggetto(nome, parti, MAT, coll, loc, extra=()):
    sedi, rotaie, trav = parti
    gruppi = [([MAT['kraft'], MAT['bordo'], MAT['interno']], sedi),
              ([MAT['vernice_grigio'], MAT['bordo'], MAT['interno']], rotaie),
              ([MAT['legno']]*3, trav)] + list(extra)
    slots = []; geos = []
    for mats, items in gruppi:
        idx = []
        for m in mats:
            if m not in slots: slots.append(m)
            idx.append(slots.index(m))
        for (V, F, M_, U, S), Mx in items:
            geos.append(((V, F, [idx[m] for m in M_], U, S), Mx))
    return make_object(nome, geos, slots, coll, loc)

def leva(MAT, p, a):
    # cassetta di manovra di cartone + leva di legno, accanto agli aghi dello scambio
    d = Vector((-math.sin(a), math.cos(a))); c = p + d*1.75
    box = [(build_panel(rect(c.x - 0.25, c.y - 0.18, c.x + 0.25, c.y + 0.18), t=0.30, rough=0.006, nick=0.01, warp=0.0, seed=7), Matrix())]
    stick = build_panel(circle(0, 0, 0.025, 8), t=0.55, rough=0.0, warp=0.0, nick=0.0)
    return [([MAT['vernice_rosso'], MAT['bordo'], MAT['interno']], box),
            ([MAT['legno']]*3, [(stick, frame_dir(Vector((c.x, c.y, 0.30)), Vector((0.35, 0, 1))))])]

def respingente(MAT, x):
    # tronchino: trave di cartone sopra due ritti, alla fine del binario
    p = [(build_panel(rect(x, -1.0, x + 0.25, 1.0), t=0.25, rough=0.006, nick=0.02, warp=0.0, seed=3), Matrix.Translation((0, 0, 0.55)))]
    p += [(build_panel(rect(x, s - 0.12, x + 0.25, s + 0.12), t=0.55, rough=0.006, nick=0.02, warp=0.0, seed=5 + i), Matrix())
          for i, s in enumerate((-0.6, 0.6))]
    return [([MAT['vernice_rosso'], MAT['bordo'], MAT['interno']], p)]

def pezzi(MAT, coll, x0):
    out = []; x = x0; passo = 32.0
    def metti(nome, titolo, parti, extra=()):
        nonlocal x
        loc = (x, RIGA_Y, 0.0)
        ob = oggetto('Binario_' + nome, parti, MAT, coll, loc, extra)
        cartellino(titolo, (x + 6.0, RIGA_Y - 4.5, 0.0), coll, MAT)
        out.append(ob); x += passo
    metti('Dritto', 'Dritto · 12 m', binario([dritto(L)], 11))
    metti('Curva', 'Curva · R 25 m, 30°', binario([curva(R, 30, 1)], 21))
    dev = curva(R, 26, -1)
    metti('Scambio', 'Scambio · dritto + deviata a destra', binario([dritto(L), dev], 31, lambda k, p: k == 1 and abs(p.y) < 2*G + 0.2),
          leva(MAT, Vector((1.2, 0)), 0.0))
    sx, dx = curva(R, 15, 1), curva(R, 15, -1)
    metti('Bivio', 'Bivio a Y · ±15°', binario([sx, dx], 41, lambda k, p: k == 1 and abs(p.y) < G + 0.2))
    metti('Incrocio', 'Incrocio · 90°', binario([dritto(L), dritto(L, (L/2, -L/2), math.pi/2)], 51))
    metti('Tronchino', 'Tronchino · fine binario', binario([dritto(8.0)], 61), respingente(MAT, 7.4))
    return out

def run():
    MAT = make_materials()
    coll = bpy.data.collections.get(ROOT)
    if coll:
        for o in list(coll.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0:
                (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.curves).remove(d)
    else:
        coll = bpy.data.collections.new(ROOT); bpy.context.scene.collection.children.link(coll)
    return pezzi(MAT, coll, 0.0)

if __name__ == '__main__':
    run()
