# =====================================================================
# cb_cavallo.py — Corsa Bis · cavallo a dondolo di cartone
# Cosa fa: costruisce il cavallo a dondolo per le statue equestri del GDD
#   (rotonda compatta: cavallo lungo 14,5 e alto 8 unità = 2,8 × 1,55 m),
#   ispirato al cavallo di legno di riferimento (BlenderKit, solo come
#   riferimento) ma nel nostro stile:
#   - due archi a dondolo di cartone spesso, uniti da due traversi di legno;
#   - quattro zampe a tavola divaricate, avvitate agli archi e al corpo
#     con perni di legno;
#   - corpo a scatola, collo e testa sagomati in un cartone spesso,
#     maniglia di legno che attraversa la testa, occhi a bottone;
#   - criniera e coda frangiate (cartone ritagliato a denti);
#   - sella con i due lembi laterali.
#   Metri reali, davanti verso +X, archi appoggiati a Z = 0, origine al
#   centro tra gli archi. Pezzi rigidi: si può far dondolare ruotando
#   l'oggetto radice attorno a Y.
# Uso: apri il file nel Text Editor e premi Run Script.
# =====================================================================
import bpy, math, os
from mathutils import Vector, Matrix

def _carica(nome):
    t = bpy.data.texts.get(nome)
    if t is not None: return t.as_string()
    raise FileNotFoundError(nome + ': aprilo nel Text Editor')

if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'box_parts' not in globals(): exec(_carica('cb_tutorial.py'))

SC = 0.35                  # scala del cartone (onda ogni ~5,6 cm)
T_A, T_Z, T_T = 0.05, 0.04, 0.10   # spessori: archi, zampe, testa e collo
R_ARCO, H_ARCO, Y_ARCO = 3.2, 0.13, 0.36
LOC = Vector((0.0, 6.0, 0.0))      # dove sta nella scena

def kw(rough=0.004, nick=0.012, step=0.25):
    # bottom_mat=0: anche il retro del foglio è dipinto (testa, archi, zampe si vedono dai due lati)
    return dict(rough=rough, warp=0.0, nick=nick, step=step, scala=1.0, bottom_mat=0)

def lato(y, s=1):
    # piano x-z a quota y, faccia esterna verso s*Y
    return frame((0, y, 0), (1, 0, 0), (0, 0, 1), (0, s, 0)) if s > 0 else frame((0, y, 0), (-1, 0, 0), (0, 0, 1), (0, -1, 0))

def specchia_x(pts):
    return [(-x, z) for x, z in reversed(pts)]

def arco_profilo():
    a = math.asin(1.35/R_ARCO); n = 24
    est = [(R_ARCO*math.sin(-a + 2*a*i/n), R_ARCO - R_ARCO*math.cos(-a + 2*a*i/n)) for i in range(n + 1)]
    r2 = R_ARCO - H_ARCO
    inn = [(r2*math.sin(a - 2*a*i/n), R_ARCO - r2*math.cos(a - 2*a*i/n)) for i in range(n + 1)]
    return est + inn

def z_arco(x):
    return R_ARCO - math.sqrt(R_ARCO**2 - x*x)

def tavola(p0, p1, w):
    # rettangolo da p0 a p1 (piano x-z) largo w
    p0 = Vector(p0); p1 = Vector(p1); d = (p1 - p0).normalized(); n = Vector((-d.y, d.x))*w/2
    return [tuple(p0 - n), tuple(p1 - n), tuple(p1 + n), tuple(p0 + n)]

def denti(p0, p1, h, n, base_su=True):
    # striscia frangiata: base dritta da p0 a p1, denti alti h
    p0 = Vector(p0); p1 = Vector(p1); d = p1 - p0; nn = Vector((-d.y, d.x)).normalized()*h
    pts = [tuple(p0), tuple(p1)]
    for i in range(n, -1, -1):
        q = p0 + d*i/n
        pts.append(tuple(q + nn*(1.0 if i % 2 == 0 else 0.45)))
    return pts

def disco(c, r, asse_y=True, n=10, t=0.02):
    g = build_panel(circle(0, 0, r, n), t=t, rough=0, warp=0, nick=0, step=5.0)
    return g, frame(Vector(c), (1, 0, 0), (0, 0, 1) if asse_y else (0, 1, 0), (0, 1 if c[1] >= 0 else -1, 0) if asse_y else (0, 0, 1))

def bacchetta(p0, d, L, r):
    g = build_panel(circle(0, 0, r, 10), t=L, rough=0, warp=0, nick=0)
    return g, frame_dir(Vector(p0), Vector(d))

def materiali():
    return {'kraft': mat_kraft('CB_C_Kraft', 1.0, SC), 'bordo': mat_bordo('CB_C_Bordo', SC*0.6), 'interno': mat_kraft('CB_C_Interno', 0.42, SC),
            'crema': mat_vernice('CB_C_Crema', (0.86, 0.80, 0.66, 1), 0.70, SC), 'grigio': mat_vernice('CB_C_Criniera', (0.10, 0.08, 0.07, 1), 0.70, SC),
            'rosso': mat_vernice('CB_C_Sella', (0.60, 0.10, 0.06, 1), 0.66, SC), 'blu': mat_vernice('CB_C_Archi', (0.12, 0.24, 0.38, 1), 0.72, SC),
            'legno': mat_legno('CB_C_Legno'), 'occhio': mat_plain('CB_C_Occhio', (0.02, 0.02, 0.02, 1), 0.2)}

def run():
    coll = bpy.data.collections.get('Cavallo_Cartone')
    if coll:
        for o in list(coll.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0: bpy.data.meshes.remove(d)
    else:
        coll = bpy.data.collections.new('Cavallo_Cartone'); bpy.context.scene.collection.children.link(coll)
    M = materiali(); C = lambda k: [M[k], M['bordo'], M['interno']]
    radice = bpy.data.objects.new('Cavallo_Dondolo', None); radice.empty_display_size = 0.5; radice.location = LOC
    coll.objects.link(radice); out = []
    def pezzo(nome, geos, mats):
        ob = make_object('CV_' + nome, geos, mats, coll); ob.parent = radice; out.append(ob); return ob
    # archi a dondolo e traversi
    pezzo('Archi', [(build_panel(arco_profilo(), t=T_A, seed=1, **kw(step=0.3)), lato(s*Y_ARCO - (T_A if s > 0 else -T_A)/2*0 + (0 if s > 0 else 0), s)) for s in (1, -1)], C('blu'))
    out[-1].data.update()
    pezzo('Traversi', [bacchetta((x, -Y_ARCO - 0.06, z_arco(x) + 0.08), (0, 1, 0), 2*Y_ARCO + 0.12, 0.025) for x in (-0.95, 0.95)], [M['legno']]*3)
    # zampe: tavole divaricate dagli archi al corpo
    zampe = []
    for s in (1, -1):
        y = s*(Y_ARCO - T_A - 0.005)
        for xb, xt in ((0.98, 0.42), (-0.98, -0.42)):
            zampe.append((build_panel(tavola((xb, z_arco(xb) + 0.02), (xt, 0.86), 0.11), t=T_Z, seed=int(10*xb) + s, **kw()),
                          lato(y - (T_Z if s > 0 else -T_Z), s)))
    pezzo('Zampe', zampe, C('kraft'))
    # corpo a scatola
    pezzo('Corpo', [(build_panel(pd['outline'], pd['holes'], t=pd['t'], seed=40 + i, **kw()), pd['M'])
                    for i, pd in enumerate(box_parts(-0.58, 0.58, -0.16, 0.16, 0.80, 1.10, t=0.03))], C('crema'))
    pezzo('Corpo_Fondo', [(build_panel(rect(-0.58, -0.16, 0.58, 0.16), t=0.03, seed=5, **kw()), frame((0, 0, 0.80), (1, 0, 0), (0, 1, 0)))], C('crema'))
    # collo e testa sagomati (cartone spesso), maniglia e occhi
    testa = [(0.40, 0.90), (0.62, 1.00), (0.78, 1.32), (0.80, 1.47), (0.74, 1.60), (0.83, 1.52), (0.90, 1.50),
             (1.18, 1.33), (1.22, 1.24), (1.16, 1.17), (0.98, 1.20), (0.86, 1.18), (0.70, 1.06), (0.52, 1.10)]
    pezzo('Testa', [(build_panel(testa, t=T_T, seed=7, **kw(step=0.12)), lato(-T_T/2, 1))], C('crema'))
    pezzo('Maniglia', [bacchetta((0.86, -0.20, 1.36), (0, 1, 0), 0.40, 0.018)], [M['legno']]*3)
    pezzo('Occhi', [disco((1.02, s*(T_T/2 + 0.001), 1.38), 0.025, n=8, t=0.012) for s in (1, -1)], [M['occhio']]*3)
    # criniera e coda frangiate
    pezzo('Criniera', [(build_panel(denti((0.50, 1.10), (0.80, 1.52), 0.09, 7), t=T_T + 0.03, seed=9, **kw(nick=0.0, step=0.5)),
                        lato(-(T_T + 0.03)/2, 1))], [M['grigio'], M['bordo'], M['grigio']])
    coda = []
    for i, ang in enumerate((150, 162, 174)):
        a = math.radians(ang); p0 = Vector((-0.56, 1.02)); p1 = p0 + Vector((math.cos(a), math.sin(a)))*0.55
        coda.append((build_panel(denti(tuple(p0), tuple(p1), 0.07, 5), t=0.03, seed=20 + i, **kw(nick=0.0, step=0.5)), lato(-0.015 + (i - 1)*0.035, 1)))
    pezzo('Coda', coda, [M['grigio'], M['bordo'], M['grigio']])
    # sella: seduta + due lembi
    sella = [(build_panel(rect(-0.20, -0.19, 0.20, 0.19), t=0.03, seed=30, **kw()), frame((0.02, 0, 1.10), (1, 0, 0), (0, 1, 0)))]
    for s in (1, -1):
        sella.append((build_panel([(-0.18, 0.86), (0.20, 0.86), (0.24, 1.12), (-0.22, 1.12)], t=0.02, seed=31 + s, **kw()), lato(s*0.16 + (0 if s > 0 else 0), s)))
    pezzo('Sella', sella, C('rosso'))
    # perni: zampe-archi e zampe-corpo
    perni = []
    for s in (1, -1):
        y = s*(Y_ARCO + 0.002)
        for xb in (0.98, -0.98): perni.append(disco((xb*0.98, y, z_arco(xb) + 0.07), 0.035))
        for xt in (0.46, -0.46): perni.append(disco((xt, s*(0.165 + 0.002), 0.92), 0.035))
    pezzo('Perni', perni, [M['legno']]*3)
    tri = sum(len(p.vertices) - 2 for o in out for p in o.data.polygons)
    return tri

if __name__ == '__main__':
    print(run())
