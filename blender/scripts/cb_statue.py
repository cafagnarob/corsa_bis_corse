# =====================================================================
# cb_statue.py — Corsa Bis · statue di cartone per le rotonde
# Cosa fa: costruisce i monumenti del GDD ("Monumenti al centro delle
#   rotonde", rotonda compatta) con l'omino di cartone in pose tipiche
#   da statua, dipinto come bronzo o marmo (la vernice si scrosta e
#   lascia vedere il kraft, i bordi mostrano l'onda del cartone):
#   - Oratore       bronzo: braccio teso che indica lontano, mano sul
#                   fianco, passo avanti, mantello
#   - Pensatore     bronzo: seduto su un masso, mento sulla mano
#   - Fiaccola      marmo: braccio alzato con la fiaccola, libro al petto
#   - Poeta         marmo: libro aperto in mano, mano sul cuore, testa china
#   - Equestre      bronzo: cavaliere sul cavallo a dondolo, spada alzata,
#                   mantello
#   Misure (GDD, rotonda compatta, in unità di gioco = metri x 5,2):
#   basamento r 24 h 3 (4,62 m x 0,58 m), piedistallo 12 x 12 x 13
#   (2,31 x 2,31 x 2,5 m) con cornici e targa, statua alta 13 (2,5 m =
#   1,43 volte l'omino); equestre su piedistallo 16 x 8 x 13.
#   Ogni monumento è UNA mesh (Monumento_<nome>) con l'origine al centro
#   della base del basamento, a Z = 0, e il davanti verso +X (il codice
#   lo gira verso il viale principale della rotonda).
# Uso: Run Script (richiede cb_lib.py, cb_omino.py, cb_personaggi.py e,
#   per l'equestre, la collection Cavallo_Cartone già costruita).
# =====================================================================
import bpy, math
from mathutils import Vector, Matrix

def _carica(nome):
    t = bpy.data.texts.get(nome)
    if t is not None: return t.as_string()
    raise FileNotFoundError(nome + ': aprilo nel Text Editor')

_n = __name__; __name__ = 'cb_statue'
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'Personaggio' not in globals(): exec(_carica('cb_personaggi.py'))
__name__ = _n

U = 1/5.2                                   # un'unità di gioco in metri
BASE_R, BASE_H = 24*U, 3*U                  # basamento
PIED = (12*U, 12*U, 13*U)                   # piedistallo della statua
PIED_EQ = (16*U, 8*U, 13*U)                 # piedistallo dell'equestre
K = 13*U/1.75                               # statua = 1,43 omini
PASSO = 11.0                                # distanza tra i monumenti nella scena
RAD = math.radians

def materiali_statue():
    return {'bronzo': mat_vernice('CB_S_Bronzo', (0.20, 0.40, 0.34, 1), 0.70, SCALA*1.5),
            'marmo': mat_vernice('CB_S_Marmo', (0.88, 0.86, 0.80, 1), 0.74, SCALA*1.5),
            'pietra': mat_vernice('CB_S_Pietra', (0.46, 0.43, 0.38, 1), 0.72, 0.6),
            'targa': mat_vernice('CB_S_Targa', (0.45, 0.32, 0.12, 1), 0.80, 0.2),
            'oro': mat_vernice('CB_S_Fiamma', (0.95, 0.62, 0.15, 1), 0.85, 0.2),
            'bordo': mat_bordo('CB_S_Bordo', 0.6), 'interno': mat_kraft('CB_S_Interno', 0.42, 0.6)}

# ---------- basamento e piedistallo ----------
def piedistallo(dim, MS):
    # basamento tondo + zoccolo + fusto + cornice, tutto cartone dipinto a pietra; targa davanti
    lx, ly, lz = dim; g = []
    g.append((build_panel(circle(0, 0, BASE_R, 48), t=BASE_H, rough=0.02, warp=0, nick=0.03, step=0.6, seed=1, scala=1.0), Matrix()))
    z = BASE_H
    for nome, (sx, sy, h) in (('zoccolo', (lx + 0.30, ly + 0.30, 0.28)), ('fusto', (lx, ly, lz - 0.56)), ('cornice', (lx + 0.24, ly + 0.24, 0.28))):
        g += scatola_spessa((0, 0, z + h/2), (sx, sy, h), 0.03, len(nome))   # scatola di 6 fogli: facce dipinte, onda solo sugli spigoli
        z += h
    mats = [MS['pietra'], MS['bordo'], MS['interno']]
    targa = (build_panel(rect(-0.45, -0.25, 0.45, 0.25), t=0.03, rough=0.004, warp=0, nick=0.01, step=0.3, seed=7, scala=1.0),
             frame((lx/2, 0, BASE_H + 0.28 + (lz - 0.56)*0.55), (0, 1, 0), (0, 0, 1), (1, 0, 0)))
    return g, mats, targa, BASE_H + lz       # quota della faccia superiore

def scatola_spessa(c, s, t, seed):
    # come la scatola dell'omino ma con cartone più spesso (piedistalli)
    hx, hy, hz = s[0]/2, s[1]/2, s[2]/2; x, y, z = c
    def f(o, fr, i): return (build_panel(o, t=t, rough=0.006, warp=0, nick=0.012, step=0.4, seed=seed + i, scala=1.0), fr)
    return [f(rect(x - hx, y - hy, x + hx, y + hy), frame((0, 0, z + hz - t), (1, 0, 0), (0, 1, 0), (0, 0, 1)), 1),
            f(rect(x - hx, -(y + hy), x + hx, -(y - hy)), frame((0, 0, z - hz + t), (1, 0, 0), (0, -1, 0), (0, 0, -1)), 2),
            f(rect(y - hy, z - hz + t, y + hy, z + hz - t), frame((x + hx - t, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0)), 3),
            f(rect(-(y + hy), z - hz + t, -(y - hy), z + hz - t), frame((x - hx + t, 0, 0), (0, -1, 0), (0, 0, 1), (-1, 0, 0)), 4),
            f(rect(-(x + hx - t), z - hz + t, -(x - hx + t), z + hz - t), frame((0, y + hy - t, 0), (-1, 0, 0), (0, 0, 1), (0, 1, 0)), 5),
            f(rect(x - hx + t, z - hz + t, x + hx - t, z + hz - t), frame((0, y - hy + t, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)), 6)]

# ---------- unione in una mesh ----------
def unisci_oggetti(objs, nome, origine, coll, rimappa):
    # objs: oggetti mesh (con le loro trasformazioni); rimappa: funzione materiale -> materiale
    V, F, MI, UV, slots = [], [], [], [], []
    for o in objs:
        me = o.data; M = Matrix.Translation(-origine) @ o.matrix_world; b0 = len(V)
        V += [tuple(M @ v.co) for v in me.vertices]; uvl = me.uv_layers.active
        mats = [s.material for s in o.material_slots]
        for p in me.polygons:
            m = rimappa(mats[p.material_index] if mats else None)
            if m not in slots: slots.append(m)
            F.append([b0 + i for i in p.vertices]); MI.append(slots.index(m))
            UV.append([tuple(uvl.data[li].uv) if uvl else (0, 0) for li in p.loop_indices])
    me = bpy.data.meshes.new(nome); me.from_pydata(V, [], F)
    uvl = me.uv_layers.new(name='UVMap')
    for p, mi, uu in zip(me.polygons, MI, UV):
        p.material_index = mi
        for k, li in enumerate(p.loop_indices): uvl.data[li].uv = uu[k]
    for m in slots: me.materials.append(m)
    me.update(); ob = bpy.data.objects.new(nome, me); coll.objects.link(ob); ob.location = origine
    return ob

def geo_obj(nome, geos, mats, coll):
    return make_object(nome, geos, mats, coll)

def posa(pg, rot):
    for osso, (rx, ry, rz) in rot.items(): pg.arm.pose.bones[osso].rotation_euler = (RAD(rx), RAD(ry), RAD(rz))
    bpy.context.view_layer.update()

def monumento(nome, coll, MS, M, centro, pittura, accessori, rot, dim=PIED, seduto=0.0, extra=None, scala=K):
    centro = Vector(centro)
    gp, mp, targa, top = piedistallo(dim, MS)
    tmp = [geo_obj(f'_{nome}_Piedistallo', gp, mp, coll), geo_obj(f'_{nome}_Targa', [targa], [MS['targa'], MS['bordo'], MS['interno']], coll)]
    for o in tmp: o.location = centro
    pg = Personaggio(f'Statua_{nome}', coll, M, centro + Vector((0, 0, top)), scala)
    if accessori: accessori(pg)
    pg.fine()
    pg.arm.location.z -= seduto*scala
    posa(pg, rot)
    objs = [o for o in pg.pezzi if o.type == 'MESH'] + tmp
    if extra: objs += extra(pg, centro, top)
    bpy.context.view_layer.update()
    tieni = {MS['bordo'], MS['interno'], MS['pietra'], MS['targa'], MS['oro'], M['bordo'], M['interno']}
    def rimappa(m):
        if m in (M['bordo'],): return MS['bordo']
        if m in (M['interno'],): return MS['interno']
        return m if m in tieni else pittura
    ob = unisci_oggetti(objs, f'Monumento_{nome}', centro, coll, rimappa)
    # via i pezzi temporanei e l'armatura
    for o in objs + [pg.arm]:
        d = o.data; bpy.data.objects.remove(o, do_unlink=True)
        if d is not None and d.users == 0:
            (bpy.data.armatures if isinstance(d, bpy.types.Armature) else bpy.data.meshes).remove(d)
    return ob

# ---------- accessori ----------
def mantello(pg):
    pina = pg.M
    g = [lastra([(-0.14, 0.0), (0.14, 0.0), (0.17, -0.55), (-0.17, -0.55)], frame((-BUSTO_X - 0.012, 0, BUSTO_Z1), (0, 1, 0), (0, 0, 1), (-1, 0, 0)), 0.012)]
    pg.aggiungi('Mantello', g, cartone(pg.M, pg.M['vestiti']), 'Busto')

def libro_aperto(pg, lato, osso):
    y = MANO_Y[lato]; z = MANO_Z0 + 0.06; g = []
    for s in (1, -1):
        g.append(lastra(rect(0, -0.07, 0.11, 0.07), frame((0.02, y, z), (0.0, s*math.cos(RAD(25)), math.sin(RAD(25))), (1, 0, 0), (0, -s*math.sin(RAD(25)), math.cos(RAD(25)))), 0.012))
    pg.aggiungi('Libro', g, [pg.M['vestiti']]*3, osso)       # pagine e copertina tutte dipinte

def fiaccola(pg):
    y = MANO_Y['Dx']; z = MANO_Z0
    g = [(build_panel(circle(0, 0, 0.025, 8), t=0.30, rough=0, warp=0, nick=0, step=5.0), Matrix.Translation((0, y, z - 0.08)))]
    pg.aggiungi('Fiaccola', g, [pg.M['vestiti']]*3, 'Avambraccio_Dx')
    # fiamma: tre lingue di cartone incrociate, dipinte d'oro (all'ingiù: il braccio verrà alzato)
    fl = [(-0.06, 0.0), (0.06, 0.0), (0.03, -0.10), (0.0, -0.18), (-0.03, -0.10)]
    g = []
    for a in (0, 60, 120):
        r = RAD(a); g.append(lastra(fl, frame((0, y, z - 0.08), (math.cos(r), math.sin(r), 0), (0, 0, 1), (-math.sin(r), math.cos(r), 0)), 0.008))
    ob = pg.aggiungi('Fiamma', g, [bpy.data.materials['CB_S_Fiamma']]*3, 'Avambraccio_Dx')

def spada(pg):
    y = MANO_Y['Dx']; z = MANO_Z0 + 0.02
    lama = [(-0.018, 0.0), (0.018, 0.0), (0.018, -0.75), (0.0, -0.82), (-0.018, -0.75)]
    g = [lastra(lama, frame((0.0, y, z), (1, 0, 0), (0, 0, 1), (0, 1, 0)), 0.01),
         lastra(rect(-0.09, -0.012, 0.09, 0.012), frame((0.0, y - 0.005, z), (1, 0, 0), (0, 0, 1), (0, 1, 0)), 0.02)]
    pg.aggiungi('Spada', g, cartone(pg.M, pg.M['vestiti']), 'Avambraccio_Dx')

def masso(pg, centro, top):
    # il masso su cui siede il pensatore (cartone accartocciato a gradoni)
    MS = bpy.data.materials
    g = [(build_panel([(-0.42, -0.30), (0.10, -0.34), (0.16, 0.30), (-0.40, 0.33)], t=0.38*K, rough=0.03, warp=0, nick=0.04, step=0.15, seed=4, scala=1.0), Matrix.Translation((0, 0, top))),
         (build_panel([(-0.45, -0.20), (-0.20, -0.22), (-0.18, 0.22), (-0.44, 0.24)], t=0.55*K, rough=0.02, warp=0, nick=0.03, step=0.15, seed=5, scala=1.0), Matrix.Translation((0, 0, top)))]
    o = make_object('_Masso', g, [MS['CB_S_Bronzo'], MS['CB_S_Bordo'], MS['CB_S_Interno']], bpy.data.collections['Statue_Cartone'])
    o.location = centro; return [o]

def cavallo(pg, centro, top):
    # copia del cavallo a dondolo di cartone sopra il piedistallo
    out = []; src = bpy.data.collections['Cavallo_Cartone']; LOCC = bpy.data.objects['Cavallo_Dondolo'].location.copy()
    for o in src.objects:
        if o.type != 'MESH': continue
        c = o.copy(); c.data = o.data.copy(); c.parent = None
        c.matrix_world = Matrix.Translation(centro + Vector((0, 0, top)) - LOCC) @ o.matrix_world
        bpy.data.collections['Statue_Cartone'].objects.link(c); out.append(c)
    return out

# ---------- pose ----------
POSE = {
    'Oratore': {'Braccio_Sup_Dx': (118, 0, -18), 'Braccio_Sup_Sx': (-8, 0, 32), 'Avambraccio_Sx': (35, 0, -95),
                'Coscia_Sx': (20, 0, 0), 'Gamba_Sx': (-14, 0, 0), 'Coscia_Dx': (-8, 0, 0), 'Testa': (-10, 0, -10), 'Busto': (-3, 0, 0)},
    'Pensatore': {'Coscia_Sx': (88, 0, 6), 'Coscia_Dx': (88, 0, -6), 'Gamba_Sx': (-92, 0, 0), 'Gamba_Dx': (-92, 0, 0),
                  'Busto': (22, 0, 0), 'Testa': (10, 0, 0), 'Braccio_Sup_Dx': (55, 0, 8), 'Avambraccio_Dx': (115, 0, 0),
                  'Braccio_Sup_Sx': (45, 0, 4), 'Avambraccio_Sx': (35, 0, 0)},
    'Fiaccola': {'Braccio_Sup_Dx': (178, 0, -6), 'Braccio_Sup_Sx': (20, 0, 8), 'Avambraccio_Sx': (95, 0, -40),
                 'Coscia_Sx': (10, 0, 0), 'Gamba_Sx': (-8, 0, 0), 'Testa': (-6, 0, 0)},
    'Poeta': {'Braccio_Sup_Sx': (28, 0, 10), 'Avambraccio_Sx': (70, 0, -10), 'Braccio_Sup_Dx': (25, 0, 0), 'Avambraccio_Dx': (105, 0, 55),
              'Testa': (16, 0, 8), 'Busto': (4, 0, 0), 'Coscia_Dx': (12, 0, 0), 'Gamba_Dx': (-10, 0, 0)},
    'Equestre': {'Coscia_Sx': (80, 0, 22), 'Coscia_Dx': (80, 0, -22), 'Gamba_Sx': (-75, 0, 0), 'Gamba_Dx': (-75, 0, 0),
                 'Braccio_Sup_Dx': (135, 0, -10), 'Braccio_Sup_Sx': (40, 0, 5), 'Avambraccio_Sx': (50, 0, 0), 'Testa': (-5, 0, 0)},
}

def run():
    coll = bpy.data.collections.get('Statue_Cartone')
    if coll:
        for o in list(coll.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0:
                (bpy.data.armatures if isinstance(d, bpy.types.Armature) else bpy.data.meshes).remove(d)
    else:
        coll = bpy.data.collections.new('Statue_Cartone'); bpy.context.scene.collection.children.link(coll)
    MS = materiali_statue(); M = materiali(); out = {}
    x0, y0 = 30.0, 0.0
    defs = [('Oratore', MS['bronzo'], mantello, None, PIED, 0.0),
            ('Pensatore', MS['bronzo'], None, masso, PIED, 0.36),
            ('Fiaccola', MS['marmo'], lambda pg: (fiaccola(pg), libro_aperto(pg, 'Sx', 'Avambraccio_Sx')), None, PIED, 0.0),
            ('Poeta', MS['marmo'], lambda pg: libro_aperto(pg, 'Sx', 'Avambraccio_Sx'), None, PIED, 0.0),
            ('Equestre', MS['bronzo'], lambda pg: (mantello(pg), spada(pg)), cavallo, PIED_EQ, -0.42)]
    for i, (nome, pit, acc, extra, dim, sed) in enumerate(defs):
        c = (x0, y0 + i*PASSO, 0.0)
        # seduto: di quanto scende l'omino (in altezze dell'omino da 1,75 m); per l'equestre è
        # negativo: il cavaliere sale sulla sella (1,13 m sopra il piedistallo)
        # equestre: il cavaliere ha la scala del cavallo a dondolo (1:1, GDD: cavallo 14,5, cavaliere +7)
        ob = monumento(nome, coll, MS, M, c, pit, acc, POSE[nome], dim, seduto=sed, extra=extra, scala=1.0 if nome == 'Equestre' else K)
        out[nome] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    return out

if __name__ == '__main__':
    print(run())
