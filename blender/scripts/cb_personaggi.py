# =====================================================================
# cb_personaggi.py — Corsa Bis · i personaggi ricorrenti del GDD
# Cosa fa: parte dall'omino di cartone (cb_omino.py, LOD0 con rig a pezzi
#   rigidi) e ne fa i cinque personaggi della tabella "Personaggi
#   ricorrenti", ognuno riconoscibile da sagoma, colori e un oggetto
#   suo, tutto di cartone come il resto del gioco:
#   - Signora Pina      pensionata, più bassa: crocchia grigia, occhiali,
#                       gonna, borsa della spesa con i porri (va al mercato)
#   - Marco             studente: felpa col cappuccio, jeans, zaino,
#                       cuffie, scarpe da ginnastica bianche
#   - Dottoressa Rinaldi medico: camice bianco lungo, divisa verde acqua,
#                       stetoscopio di spago, coda di cavallo, cartellino
#   - Ingegner Ferretti pendolare: completo blu, camicia e cravatta rossa,
#                       occhiali, valigetta
#   - Giulia e Tommaso  i baristi: grembiuli bordeaux; lei capelli lunghi,
#                       lui barba e vassoio con due tazzine
#   Ogni personaggio ha la sua armatura (stesse 11 ossa dell'omino): gli
#   accessori sono figli dell'osso giusto (zaino sul busto, borsa e
#   valigetta sull'avambraccio, coda sulla testa...). L'altezza diversa è
#   la scala dell'armatura (Pina 1,61 m, Marco 1,79 m...).
#   Metri reali, davanti verso +X, origine in mezzo ai piedi (come l'omino).
# Uso: Run Script (richiede cb_lib.py e cb_omino.py nel Text Editor).
# =====================================================================
import bpy, math
from mathutils import Vector, Matrix

def _carica(nome):
    t = bpy.data.texts.get(nome)
    if t is not None: return t.as_string()
    raise FileNotFoundError(nome + ': aprilo nel Text Editor')

_n = __name__; __name__ = 'cb_personaggi'
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'costruisci' not in globals(): exec(_carica('cb_omino.py'))
__name__ = _n

# misure utili dell'omino (metri, prima della scala del personaggio)
TESTA_Z, TESTA_L = 11.61*S, 2.49*S          # centro e lato della testa (cubo)
TESTA_TOP = TESTA_Z + TESTA_L/2
BUSTO_Z0, BUSTO_Z1 = (7.75 - 1.83)*S, (7.75 + 1.83)*S
BUSTO_X, BUSTO_Y = 2.17*S/2, 2.49*S/2        # mezza profondità e mezza larghezza
MANO_Y = {'Sx': P(0, -1.92, 0).y, 'Dx': P(0, 1.41, 0).y}
MANO_Z0 = (3.30 - 0.33)*S                    # fondo della mano

def vern(nome, col, chips=0.74):
    return mat_vernice('CB_P_' + nome, (*col, 1), chips, SCALA*1.5)

def box(c, s):
    return scatola(Vector(c), Vector(s))     # scatola di 6 fogli dell'omino

def lastra(outline, frame_m, t=SP, holes=()):
    return build_panel(outline, holes=holes, t=t, rough=0.001, warp=0.0, nick=0.0, step=5.0, seed=len(outline)), frame_m

def tubo(punti, r, mat, coll, nome):
    cu = bpy.data.curves.new(nome, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 1
    sp = cu.splines.new('POLY'); sp.points.add(len(punti) - 1)
    for i, p in enumerate(punti): sp.points[i].co = (*p, 1)
    ob = bpy.data.objects.new(nome + '_tmp', cu); coll.objects.link(ob)
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    me.name = nome; me.materials.clear(); me.materials.append(mat)
    o = bpy.data.objects.new(nome, me); coll.objects.link(o); return o

class Personaggio:
    def __init__(self, nome, coll, M, loc, scala):
        self.nome, self.coll, self.M, self.loc = nome, coll, M, Vector(loc)
        self.arm, self.pezzi = costruisci(coll, M, self.loc, False)
        self.arm.name = f'PG_{nome}_Rig'; self.arm.data.name = f'PG_{nome}_Rig'
        for o in self.pezzi:
            o.name = o.name.split('.')[0].replace('OM0_', f'PG_{nome}_')
            if o.data: o.data.name = o.name
        self.scala = scala
    def colora(self, parti, mat):
        # cambia il materiale "vestiti" (slot 0) dei pezzi indicati
        for o in self.pezzi:
            if any(o.name.endswith('_' + p) for p in parti) and o.data.materials:
                o.data.materials[0] = mat
    def scarpe(self, mat):
        for o in self.pezzi:
            if '_Scarpa_' in o.name: o.data.materials[0] = mat; o.data.materials[1] = mat; o.data.materials[2] = mat
    def aggiungi(self, nome, geos, mats, osso):
        # geos in coordinate dell'omino (origine ai piedi); diventa figlio dell'osso
        ob = make_object(f'PG_{self.nome}_{nome}', geos, mats, self.coll); return self.attacca(ob, osso)
    def attacca(self, ob, osso):
        ob.location = self.loc + ob.location; bpy.context.view_layer.update(); mw = ob.matrix_world.copy()
        ob.parent = self.arm; ob.parent_type = 'BONE'; ob.parent_bone = osso
        bpy.context.view_layer.update(); ob.matrix_world = mw; self.pezzi.append(ob); return ob
    def fine(self):
        self.arm.scale = (self.scala,)*3
        return sum(len(p.vertices) - 2 for o in self.pezzi if o.type == 'MESH' for p in o.data.polygons)

def cartone(M, mat):
    return [mat, M['bordo'], M['interno']]

# ---------- accessori comuni ----------
def capelli(pg, mat, coda=None, lunghi=False, crocchia=False):
    L = TESTA_L; h = 0.045
    g = box((0, 0, TESTA_TOP + h/2 - 0.008), (L + 0.03, L + 0.03, h))            # calotta
    g += box((-L/2 - 0.012, 0, TESTA_Z + 0.03), (0.035, L + 0.03, L*0.8))       # nuca
    g += box((L/2 - 0.03, 0, TESTA_TOP - 0.025), (0.08, L + 0.03, 0.06))         # frangia: i capelli si vedono anche davanti
    for s in (1, -1): g += box((-0.02, s*(L/2 + 0.012), TESTA_TOP - 0.06), (L*0.8, 0.03, 0.12))   # basette
    if lunghi:
        g += box((-L/2 - 0.02, 0, TESTA_Z - 0.16), (0.05, L + 0.02, 0.22))     # capelli sulle spalle
        for s in (1, -1): g += box((-0.03, s*(L/2 + 0.012), TESTA_Z - 0.02), (L*0.75, 0.03, L*0.75))
    if crocchia:
        gc = build_panel(circle(0, 0, 0.07, 12), t=0.07, rough=0.001, warp=0, nick=0, step=5.0, seed=5)
        g.append((gc, frame((-0.09, 0, TESTA_TOP - 0.03), (0, 1, 0), (0, 0, 1), (1, 0, 0))))
    pg.aggiungi('Capelli', g, cartone(pg.M, mat), 'Testa')
    if coda:
        pg.aggiungi('Coda', box((-L/2 - 0.05, 0, TESTA_Z - 0.04), (0.06, 0.07, 0.20)), cartone(pg.M, mat), 'Testa')

def occhiali(pg, mat):
    x = TESTA_L/2 + 0.006; g = []
    for s in (1, -1):
        g.append(lastra(circle(0, 0, 0.042, 12), frame((x, s*0.075, TESTA_Z + 0.02), (0, 1, 0), (0, 0, 1), (1, 0, 0)), 0.006,
                        holes=[circle(0, 0, 0.032, 12)]))
    g.append(lastra(rect(-0.035, -0.006, 0.035, 0.006), frame((x, 0, TESTA_Z + 0.03), (0, 1, 0), (0, 0, 1), (1, 0, 0)), 0.006))
    pg.aggiungi('Occhiali', g, [mat]*3, 'Testa')

def grembiule(pg, mat):
    x = BUSTO_X + 0.004
    g = [lastra([(-0.12, -0.42), (0.12, -0.42), (0.13, 0.0), (0.09, 0.06), (0.09, 0.14), (-0.09, 0.14), (-0.09, 0.06), (-0.13, 0.0)],
                frame((x, 0, 0.95), (0, 1, 0), (0, 0, 1), (1, 0, 0)), 0.008)]
    for s in (1, -1):    # lacci intorno alla vita
        g.append(lastra(rect(-BUSTO_X, -0.012, BUSTO_X, 0.012), frame((0, s*(BUSTO_Y + 0.003), 0.95), (1, 0, 0), (0, 0, 1), (0, s, 0)), 0.004))
    pg.aggiungi('Grembiule', g, cartone(pg.M, mat), 'Busto')

# ---------- i cinque personaggi ----------
def pina(coll, M, loc):
    pg = Personaggio('Pina', coll, M, loc, 0.92)
    giacca = vern('Pina_Giacca', (0.52, 0.38, 0.58)); gonna = vern('Pina_Gonna', (0.22, 0.22, 0.26))
    pg.colora(('Busto', 'Braccio_Sup_Sx', 'Braccio_Sup_Dx', 'Avambraccio_Sx', 'Avambraccio_Dx'), giacca)
    pg.colora(('Coscia_Sx', 'Coscia_Dx', 'Gamba_Sx', 'Gamba_Dx'), vern('Pina_Calze', (0.62, 0.50, 0.42)))
    capelli(pg, vern('Pina_Capelli', (0.80, 0.80, 0.78)), crocchia=True)
    occhiali(pg, M['filo'])
    # gonna a campana: tronco di piramide dalla cintura alle ginocchia
    zt, zb = 0.81, 0.40
    prof = [(-0.15, zb), (0.15, zb), (0.12, zt), (-0.12, zt)]
    g = [lastra(prof, frame((0, 0.19, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)), 0.38)]
    pg.aggiungi('Gonna', g, [gonna]*3, 'Busto')          # solido pieno: tutte le facce nel colore della gonna
    # borsa della spesa a quadri con i porri, nella mano destra
    y = MANO_Y['Dx'] - 0.03; zt = MANO_Z0 - 0.02
    sac = vern('Pina_Borsa', (0.65, 0.12, 0.10), 0.80)
    g = box((0.02, y, zt - 0.13), (0.28, 0.11, 0.25))
    pg.aggiungi('Borsa', g, cartone(M, sac), 'Avambraccio_Dx')
    manici = [lastra(rect(-0.10, 0, 0.10, 0.05), frame((0.02, y, zt), (1, 0, 0), (0, 0, 1), (0, 1, 0)), 0.006,
                     holes=[rect(-0.07, 0.0, 0.07, 0.035)])]
    pg.aggiungi('Borsa_Manici', manici, [sac]*3, 'Avambraccio_Dx')
    porro = vern('Pina_Porri', (0.30, 0.52, 0.22), 0.85); bianco = vern('Pina_Porri_Bianco', (0.85, 0.85, 0.75), 0.85)
    for i, (dx, dy) in enumerate(((0.06, 0.02), (0.09, -0.02))):
        # gambo bianco dentro la borsa, foglie verdi che escono di 20 cm
        gb = build_panel(circle(0, 0, 0.018, 8), t=0.22, rough=0, warp=0, nick=0, step=5.0)
        gv = build_panel(circle(0, 0, 0.02, 8), t=0.22, rough=0, warp=0, nick=0, step=5.0)
        R = Matrix.Translation((dx, y + dy, zt - 0.20)) @ Matrix.Rotation(-0.25, 4, 'Y')
        ob = make_object(f'PG_Pina_Porro_{i}', [(gb, R), (gv, R @ Matrix.Translation((0, 0, 0.22)))], [bianco, bianco, bianco], coll)
        for p in ob.data.polygons:
            if sum(ob.data.vertices[k].co.z for k in p.vertices)/len(p.vertices) > R.translation.z + 0.2: p.material_index = 1
        ob.data.materials[1] = porro
        pg.attacca(ob, 'Avambraccio_Dx')
    return pg

def marco(coll, M, loc):
    pg = Personaggio('Marco', coll, M, loc, 1.02)
    felpa = vern('Marco_Felpa', (0.25, 0.50, 0.32)); jeans = vern('Marco_Jeans', (0.18, 0.28, 0.48))
    pg.colora(('Busto', 'Braccio_Sup_Sx', 'Braccio_Sup_Dx', 'Avambraccio_Sx', 'Avambraccio_Dx'), felpa)
    pg.colora(('Coscia_Sx', 'Coscia_Dx', 'Gamba_Sx', 'Gamba_Dx'), jeans)
    pg.scarpe(vern('Marco_Scarpe', (0.90, 0.90, 0.88), 0.85))
    capelli(pg, vern('Marco_Capelli', (0.16, 0.10, 0.06)))
    pg.aggiungi('Cappuccio', box((-BUSTO_X - 0.02, 0, BUSTO_Z1 + 0.02), (0.08, 0.24, 0.12)), cartone(M, felpa), 'Busto')
    zaino = vern('Marco_Zaino', (0.85, 0.45, 0.12))
    g = box((-BUSTO_X - 0.075, 0, 1.03), (0.14, 0.28, 0.38)) + box((-BUSTO_X - 0.155, 0, 0.98), (0.03, 0.20, 0.16))
    pg.aggiungi('Zaino', g, cartone(M, zaino), 'Busto')
    g = []
    for s in (1, -1):   # spallacci
        g.append(lastra(rect(-0.022, BUSTO_Z1 - 0.20, 0.022, BUSTO_Z1), frame((BUSTO_X + 0.004, s*0.10, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0)), 0.008))
    pg.aggiungi('Spallacci', g, [zaino]*3, 'Busto')
    # cuffie: archetto sopra la testa e due padiglioni
    nero = vern('Marco_Cuffie', (0.05, 0.05, 0.06))
    R = TESTA_L/2 + 0.03
    arco = [(0.0, R*math.cos(a), TESTA_Z + 0.02 + R*math.sin(a)) for a in [math.radians(d) for d in range(0, 181, 15)]]
    o = tubo(arco, 0.012, nero, coll, 'PG_Marco_Cuffie_Archetto'); pg.attacca(o, 'Testa')
    g = []
    for s in (1, -1): g += box((0, s*(TESTA_L/2 + 0.018), TESTA_Z), (0.08, 0.035, 0.10))
    pg.aggiungi('Cuffie', g, cartone(M, nero), 'Testa')
    return pg

def rinaldi(coll, M, loc):
    pg = Personaggio('Rinaldi', coll, M, loc, 0.97)
    camice = vern('Rinaldi_Camice', (0.93, 0.93, 0.90), 0.85); divisa = vern('Rinaldi_Divisa', (0.30, 0.62, 0.60))
    pg.colora(('Busto', 'Braccio_Sup_Sx', 'Braccio_Sup_Dx', 'Avambraccio_Sx', 'Avambraccio_Dx'), camice)
    pg.colora(('Coscia_Sx', 'Coscia_Dx', 'Gamba_Sx', 'Gamba_Dx'), divisa)
    capelli(pg, vern('Rinaldi_Capelli', (0.30, 0.15, 0.07)), coda=True)
    # falde del camice dalla cintura al ginocchio, aperte davanti
    g = []
    zt, zb = BUSTO_Z0 + 0.02, 0.43
    g += box((-0.01, 0, (zt + zb)/2), (2*BUSTO_X + 0.02, 2*BUSTO_Y + 0.02, zt - zb))
    pg.aggiungi('Camice', g, cartone(M, camice), 'Busto')
    # stetoscopio di spago intorno al collo
    grigio = vern('Rinaldi_Stetoscopio', (0.15, 0.15, 0.17))
    pts = [(BUSTO_X + 0.01, 0.05, 1.12), (BUSTO_X + 0.01, 0.06, 1.24), (0.05, 0.07, BUSTO_Z1 + 0.01), (-0.06, 0.0, BUSTO_Z1 + 0.02),
           (0.05, -0.07, BUSTO_Z1 + 0.01), (BUSTO_X + 0.01, -0.06, 1.24), (BUSTO_X + 0.01, -0.05, 1.08)]
    o = tubo(pts, 0.007, grigio, coll, 'PG_Rinaldi_Stetoscopio'); pg.attacca(o, 'Busto')
    gd = build_panel(circle(0, 0, 0.022, 10), t=0.01, rough=0, warp=0, nick=0, step=5.0)
    pg.aggiungi('Stetoscopio_Disco', [(gd, frame((BUSTO_X + 0.012, -0.05, 1.07), (0, 1, 0), (0, 0, 1), (1, 0, 0)))], [grigio]*3, 'Busto')
    blu = vern('Rinaldi_Cartellino', (0.25, 0.40, 0.70))
    pg.aggiungi('Cartellino', [lastra(rect(-0.03, -0.02, 0.03, 0.02), frame((BUSTO_X + 0.005, 0.09, 1.18), (0, 1, 0), (0, 0, 1), (1, 0, 0)), 0.006)], [blu]*3, 'Busto')
    return pg

def ferretti(coll, M, loc):
    pg = Personaggio('Ferretti', coll, M, loc, 1.0)
    blu = vern('Ferretti_Completo', (0.12, 0.16, 0.30))
    pg.colora(('Busto', 'Braccio_Sup_Sx', 'Braccio_Sup_Dx', 'Avambraccio_Sx', 'Avambraccio_Dx', 'Coscia_Sx', 'Coscia_Dx', 'Gamba_Sx', 'Gamba_Dx'), blu)
    capelli(pg, vern('Ferretti_Capelli', (0.45, 0.43, 0.40)))
    occhiali(pg, M['scarpe'])
    x = BUSTO_X + 0.004; bianco = vern('Ferretti_Camicia', (0.92, 0.92, 0.90), 0.85); rosso = vern('Ferretti_Cravatta', (0.70, 0.08, 0.08))
    camicia = [lastra([(-0.07, 0.0), (0.07, 0.0), (0.0, -0.13)], frame((x, 0, BUSTO_Z1 - 0.002), (0, 1, 0), (0, 0, 1), (1, 0, 0)), 0.005)]
    pg.aggiungi('Camicia', camicia, [bianco]*3, 'Busto')
    cr = [lastra([(-0.014, 0.0), (0.014, 0.0), (0.026, -0.27), (0.0, -0.31), (-0.026, -0.27)], frame((x + 0.005, 0, BUSTO_Z1 - 0.02), (0, 1, 0), (0, 0, 1), (1, 0, 0)), 0.005)]
    pg.aggiungi('Cravatta', cr, [rosso]*3, 'Busto')
    # valigetta nella mano destra
    pelle = vern('Ferretti_Valigetta', (0.30, 0.16, 0.07))
    y = MANO_Y['Dx'] - 0.02; zt = MANO_Z0 - 0.03
    g = box((0.0, y, zt - 0.14), (0.38, 0.09, 0.27))
    pg.aggiungi('Valigetta', g, cartone(M, pelle), 'Avambraccio_Dx')
    pg.aggiungi('Valigetta_Maniglia', [lastra(rect(-0.06, 0, 0.06, 0.045), frame((0, y, zt - 0.005), (1, 0, 0), (0, 0, 1), (0, 1, 0)), 0.01,
                                          holes=[rect(-0.04, 0.0, 0.04, 0.03)])], [M['scarpe']]*3, 'Avambraccio_Dx')
    return pg

def giulia(coll, M, loc):
    pg = Personaggio('Giulia', coll, M, loc, 0.95)
    pg.colora(('Busto', 'Braccio_Sup_Sx', 'Braccio_Sup_Dx', 'Avambraccio_Sx', 'Avambraccio_Dx'), vern('Giulia_Maglia', (0.85, 0.62, 0.15)))
    pg.colora(('Coscia_Sx', 'Coscia_Dx', 'Gamba_Sx', 'Gamba_Dx'), vern('Giulia_Pantaloni', (0.15, 0.14, 0.16)))
    capelli(pg, vern('Giulia_Capelli', (0.48, 0.20, 0.08)), lunghi=True)
    grembiule(pg, vern('Bar_Grembiule', (0.45, 0.08, 0.12)))
    return pg

def tommaso(coll, M, loc):
    pg = Personaggio('Tommaso', coll, M, loc, 1.03)
    pg.colora(('Busto', 'Braccio_Sup_Sx', 'Braccio_Sup_Dx', 'Avambraccio_Sx', 'Avambraccio_Dx'), vern('Tommaso_Camicia', (0.90, 0.90, 0.86), 0.85))
    pg.colora(('Coscia_Sx', 'Coscia_Dx', 'Gamba_Sx', 'Gamba_Dx'), vern('Tommaso_Pantaloni', (0.20, 0.17, 0.14)))
    capo = vern('Tommaso_Capelli', (0.12, 0.08, 0.05))
    capelli(pg, capo)
    L = TESTA_L; x = L/2 + 0.008
    g = box((x - 0.04, 0, TESTA_Z - L/2 + 0.05), (0.10, L + 0.01, 0.10))           # barba sul mento e sulle guance
    pg.aggiungi('Barba', g, cartone(M, capo), 'Testa')
    grembiule(pg, bpy.data.materials['CB_P_Bar_Grembiule'])
    # vassoio con due tazzine nella mano destra
    acc = vern('Tommaso_Vassoio', (0.70, 0.70, 0.72), 0.85); taz = vern('Tommaso_Tazzine', (0.95, 0.95, 0.93), 0.9)
    y = MANO_Y['Dx'] - 0.10; z = MANO_Z0 + 0.03
    gv = build_panel(circle(0, 0, 0.17, 16), t=0.012, rough=0.001, warp=0, nick=0, step=5.0, seed=9)
    pg.aggiungi('Vassoio', [(gv, Matrix.Translation((0.10, y, z)))], [acc, acc, acc], 'Avambraccio_Dx')
    g = []
    for dx, dy in ((0.05, 0.05), (0.15, -0.04)):
        gt = build_panel(circle(0, 0, 0.03, 10), t=0.045, rough=0, warp=0, nick=0, step=5.0)
        g.append((gt, Matrix.Translation((dx, y + dy, z + 0.012))))
    pg.aggiungi('Tazzine', g, [taz]*3, 'Avambraccio_Dx')
    return pg

def run():
    coll = bpy.data.collections.get('Personaggi_GDD')
    if coll:
        for o in list(coll.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0:
                (bpy.data.armatures if isinstance(d, bpy.types.Armature) else bpy.data.meshes).remove(d)
    else:
        coll = bpy.data.collections.new('Personaggi_GDD'); bpy.context.scene.collection.children.link(coll)
    M = materiali(); out = {}
    # in fila lungo Y (tutti guardano verso +X); Giulia e Tommaso affiancati
    for i, f in enumerate((pina, marco, rinaldi, ferretti, giulia, tommaso)):
        y = -2.5 + min(i, 4)*1.0 + (0.6 if f is tommaso else 0.0)
        pg = f(coll, M, (12.0, y, 0.0))
        out[pg.nome] = pg.fine()
    return out

if __name__ == '__main__':
    print(run())
