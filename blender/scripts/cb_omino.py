# =====================================================================
# cb_omino.py — Corsa Bis · l'omino di cartone (personaggio di base)
# Cosa fa: costruisce il manichino del GDD ("Personaggi: l'omino di base")
#   partendo dalle forme del prototipo (prova personaggio.blend): testa a
#   cubo, collo a molla, busto, braccia e gambe a blocchi, perni ai giunti.
#   - in metri reali, alto 1,75 m (in gioco ×5,2 = 9,1 unità, scala del codice);
#   - davanti verso +X, origine in mezzo ai piedi a Z = 0;
#   - LOD0 (personaggi principali, ~1.500 triangoli): ogni blocco è una
#     scatola di cartone chiusa (6 fogli spessi 1,2 cm, bordo ondulato
#     visibile), perni di legno a spalle, gomiti, anche e ginocchia, molla
#     di filo, cintura, due bottoni, scarpe sagomate;
#   - LOD1 (comparse, ~200 triangoli): scatole semplici senza spessore,
#     collo a prisma, tre materiali;
#   - materiali: "vestiti" (cartoncino chiaro: il colore lo dà il codice
#     per istanza), "pelle" = kraft naturale (testa e mani), scarpe scure;
#   - rig a pezzi rigidi: un osso per pezzo, nessuna deformazione.
#   Ottimizzazione: niente angoli smussati né bordi ricampionati (i blocchi
#   sono piccoli: lo storto lo dà l'onda del bordo, che è solo materiale).
# Uso: apri il file nel Text Editor e premi Run Script.
# =====================================================================
import bpy, math, os
from mathutils import Vector, Matrix

def _carica(nome):
    t = bpy.data.texts.get(nome)
    if t is not None: return t.as_string()
    raise FileNotFoundError(nome + ': aprilo nel Text Editor')

if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))

S = 1.75/12.85                      # dal prototipo (alto 12,85) ai metri reali
Y0 = -0.24                          # asse del prototipo
SP = 0.012                          # spessore del cartone dell'omino
SCALA = 0.08                        # scala del cartone (onda del bordo ogni ~1,3 cm)

def P(x, y, z):
    # prototipo (guarda verso -X) -> omino (guarda verso +X): rotazione di 180° attorno a Z
    return Vector((-x*S, -(y - Y0)*S, z*S))

def D(sx, sy, sz): return Vector((sx*S, sy*S, sz*S))

# pezzi: nome, centro (prototipo), misure (prototipo), materiale, osso
PEZZI = [
    ('Testa',            (0, -0.24, 11.61), (2.49, 2.49, 2.49), 'pelle',   'Testa'),
    ('Busto',            (0, -0.24, 7.75),  (2.17, 2.49, 3.66), 'vestiti', 'Busto'),
    ('Cintura',          (0, -0.24, 6.12),  (2.25, 2.57, 0.42), 'scarpe',  'Busto'),
    ('Braccio_Sup_Sx',   (0, -1.92, 7.88),  (0.63, 0.85, 3.15), 'vestiti', 'Braccio_Sup_Sx'),
    ('Braccio_Sup_Dx',   (0, 1.41, 7.88),   (0.63, 0.85, 3.15), 'vestiti', 'Braccio_Sup_Dx'),
    ('Avambraccio_Sx',   (0, -1.92, 4.95),  (0.63, 0.85, 2.65), 'vestiti', 'Avambraccio_Sx'),
    ('Avambraccio_Dx',   (0, 1.41, 4.95),   (0.63, 0.85, 2.65), 'vestiti', 'Avambraccio_Dx'),
    ('Mano_Sx',          (0, -1.92, 3.30),  (0.55, 0.70, 0.66), 'pelle',   'Avambraccio_Sx'),
    ('Mano_Dx',          (0, 1.41, 3.30),   (0.55, 0.70, 0.66), 'pelle',   'Avambraccio_Dx'),
    ('Coscia_Sx',        (0, -0.83, 4.56),  (0.80, 0.92, 2.71), 'vestiti', 'Coscia_Sx'),
    ('Coscia_Dx',        (0, 0.36, 4.56),   (0.80, 0.92, 2.71), 'vestiti', 'Coscia_Dx'),
    ('Gamba_Sx',         (0, -0.83, 1.75),  (0.80, 0.92, 2.20), 'vestiti', 'Gamba_Sx'),
    ('Gamba_Dx',         (0, 0.36, 1.75),   (0.80, 0.92, 2.20), 'vestiti', 'Gamba_Dx'),
]
# perni di legno sul lato esterno dei giunti: (prototipo y del pezzo, z, lato, osso)
PERNI = [(-1.92, 9.05, 'Sx', 'Braccio_Sup_Sx'), (1.41, 9.05, 'Dx', 'Braccio_Sup_Dx'),
         (-1.92, 6.30, 'Sx', 'Avambraccio_Sx'), (1.41, 6.30, 'Dx', 'Avambraccio_Dx'),
         (-0.83, 5.55, 'Sx', 'Coscia_Sx'), (0.36, 5.55, 'Dx', 'Coscia_Dx'),
         (-0.83, 3.10, 'Sx', 'Gamba_Sx'), (0.36, 3.10, 'Dx', 'Gamba_Dx')]
# ossa: nome, testa, coda (prototipo), genitore
OSSA = [('Root', (0, -0.24, 0), (-2.0, -0.24, 0), None),
        ('Busto', (0, -0.24, 5.95), (0, -0.24, 9.6), 'Root'),
        ('Testa', (0, -0.24, 9.6), (0, -0.24, 12.9), 'Busto'),
        ('Braccio_Sup_Sx', (0, -1.92, 9.05), (0, -1.92, 6.3), 'Busto'),
        ('Braccio_Sup_Dx', (0, 1.41, 9.05), (0, 1.41, 6.3), 'Busto'),
        ('Avambraccio_Sx', (0, -1.92, 6.3), (0, -1.92, 2.95), 'Braccio_Sup_Sx'),
        ('Avambraccio_Dx', (0, 1.41, 6.3), (0, 1.41, 2.95), 'Braccio_Sup_Dx'),
        ('Coscia_Sx', (0, -0.83, 5.55), (0, -0.83, 3.1), 'Root'),
        ('Coscia_Dx', (0, 0.36, 5.55), (0, 0.36, 3.1), 'Root'),
        ('Gamba_Sx', (0, -0.83, 3.1), (0, -0.83, 0.0), 'Coscia_Sx'),
        ('Gamba_Dx', (0, 0.36, 3.1), (0, 0.36, 0.0), 'Coscia_Dx')]

# ---------- materiali ----------
def materiali():
    return {'pelle': mat_kraft('CB_P_Pelle', 1.05, SCALA*1.5), 'vestiti': mat_vernice('CB_P_Vestiti', (0.80, 0.79, 0.75, 1), 0.74, SCALA*1.5),
            'scarpe': mat_vernice('CB_P_Scarpe', (0.06, 0.05, 0.05, 1), 0.72, SCALA*1.5), 'bordo': mat_bordo('CB_P_Bordo', SCALA),
            'interno': mat_kraft('CB_P_Interno', 0.42, SCALA), 'legno': mat_legno('CB_P_Legno'),
            'bottone': mat_plain('CB_P_Bottone', (0.55, 0.10, 0.05, 1), 0.3), 'filo': mat_plain('CB_P_Filo', (0.35, 0.33, 0.30, 1), 0.4)}

def foglio(outline, M):
    return build_panel(outline, t=SP, rough=0.0012, warp=0.0, nick=0.0, step=5.0, seed=len(outline)), M

def scatola(c, s):
    # scatola chiusa di 6 fogli: coperchio e fondo interi, fianchi tra i due
    hx, hy, hz = s.x/2, s.y/2, s.z/2; t = SP; x, y, z = c
    return [foglio(rect(x - hx, y - hy, x + hx, y + hy), frame((0, 0, z + hz - t), (1, 0, 0), (0, 1, 0), (0, 0, 1))),
            foglio(rect(x - hx, -(y + hy), x + hx, -(y - hy)), frame((0, 0, z - hz + t), (1, 0, 0), (0, -1, 0), (0, 0, -1))),
            foglio(rect(y - hy, z - hz + t, y + hy, z + hz - t), frame((x + hx - t, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0))),
            foglio(rect(-(y + hy), z - hz + t, -(y - hy), z + hz - t), frame((x - hx + t, 0, 0), (0, -1, 0), (0, 0, 1), (-1, 0, 0))),
            foglio(rect(-(x + hx - t), z - hz + t, -(x - hx + t), z + hz - t), frame((0, y + hy - t, 0), (-1, 0, 0), (0, 0, 1), (0, 1, 0))),
            foglio(rect(x - hx + t, z - hz + t, x + hx - t, z + hz - t), frame((0, y - hy + t, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)))]

def cubo(c, s):
    # LOD1: scatola semplice, 12 triangoli, senza spessore
    g = build_panel(rect(c.x - s.x/2, c.y - s.y/2, c.x + s.x/2, c.y + s.y/2), t=s.z, rough=0, warp=0, nick=0, step=50.0)
    return g, Matrix.Translation((0, 0, c.z - s.z/2))

def scarpa(lato_y, lod):
    # profilo laterale della scarpa (punta arrotondata verso +X), estruso lungo y
    prof = [(-0.13, 0.0), (0.17, 0.0), (0.19, 0.03), (0.18, 0.06), (0.10, 0.09), (-0.08, 0.09), (-0.13, 0.07)]
    w = 0.92*S; y0 = lato_y - w/2
    if lod: return build_panel(prof, t=w, rough=0, warp=0, nick=0, step=50.0), frame((0, y0, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0))
    return build_panel(prof, t=w, rough=0.001, warp=0.0, nick=0.004, step=5.0, seed=3), frame((0, y0, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0))

def perno(c, lato, r=0.035, n=8):
    s = 1 if lato == 'Sx' else -1
    g = build_panel(circle(0, 0, r, n), t=0.012, rough=0, warp=0, nick=0, step=5.0)
    return g, frame(c, (1, 0, 0), (0, 0, s), (0, s, 0))

def molla(coll, mat, lod):
    # filo a elica fra busto e testa (LOD1: un prisma esagonale)
    z0, z1, r = 9.55*S, 10.40*S, 0.028
    if lod:
        g = build_panel(circle(0, 0, 0.02, 6), t=z1 - z0, rough=0, warp=0, nick=0, step=50.0)
        return make_object('OM1_Collo', [(g, Matrix.Translation((0, 0, z0)))], [mat]*3, coll)
    cu = bpy.data.curves.new('Molla', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.005; cu.bevel_resolution = 0
    sp = cu.splines.new('POLY'); giri, passi = 4, 6; n = giri*passi
    sp.points.add(n)
    for i in range(n + 1):
        a = 2*math.pi*i/passi; sp.points[i].co = (r*math.cos(a), r*math.sin(a), z0 + (z1 - z0)*i/n, 1)
    ob = bpy.data.objects.new('OM0_Molla_tmp', cu); coll.objects.link(ob)
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    me.name = 'OM0_Molla'; me.materials.clear(); me.materials.append(mat)
    o = bpy.data.objects.new('OM0_Molla', me); coll.objects.link(o); return o

# ---------- costruzione ----------
def costruisci(coll, M, loc, lod):
    pref = 'OM1_' if lod else 'OM0_'; pezzi = []
    for nome, c, s, mk, osso in PEZZI:
        c = P(*c); d = D(*s); mm = [M[mk], M['bordo'] if not lod else M[mk], M['interno'] if not lod else M[mk]]
        geos = [cubo(c, d)] if lod else scatola(c, d)
        pezzi.append((make_object(pref + nome, geos, mm, coll), osso))
    for lato, y in (('Sx', -0.83), ('Dx', 0.36)):
        ob = make_object(f'{pref}Scarpa_{lato}', [scarpa(P(0, y, 0).y, lod)], [M['scarpe']]*3, coll)   # profilo estruso: i fianchi sono la tomaia, niente onda
        pezzi.append((ob, f'Gamba_{lato}'))
    if not lod:
        for yp, z, lato, osso in PERNI:
            c = P(0, yp, z); s = 1 if lato == 'Sx' else -1
            c.y += s*(0.85*S/2 if 'Braccio' in osso or 'Avambraccio' in osso else 0.92*S/2)
            pezzi.append((make_object(f'OM0_Perno_{osso}', [perno(c, lato)], [M['legno']]*3, coll), osso))
        bott = [perno(P(-1.085, -0.24 + dy, z), 'Sx', 0.022, 8) for dy, z in ((0, 8.6), (0, 7.4))]
        bott = [(g, frame(Vector((-(-1.085)*S, 0, z*S)), (0, 1, 0), (0, 0, 1), (1, 0, 0))) for (g, _), z in zip(bott, (8.6, 7.4))]
        pezzi.append((make_object('OM0_Bottoni', bott, [M['bottone']]*3, coll), 'Busto'))
    pezzi.append((molla(coll, M['filo'], lod), 'Busto'))
    # armatura
    arm_d = bpy.data.armatures.new(pref + 'Rig'); arm_d.display_type = 'STICK'
    arm = bpy.data.objects.new(pref + 'Rig', arm_d); coll.objects.link(arm); arm.location = loc; arm.show_in_front = True
    if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for nome, h, t, par in OSSA:
        b = arm_d.edit_bones.new(nome); b.head = P(*h); b.tail = P(*t)
        if par: b.parent = arm_d.edit_bones[par]
        b.align_roll(Vector((1, 0, 0)) if nome != 'Root' else Vector((0, 0, 1)))
    bpy.ops.object.mode_set(mode='POSE')
    for b in arm.pose.bones: b.rotation_mode = 'XYZ'
    bpy.ops.object.mode_set(mode='OBJECT')
    for ob, osso in pezzi:
        ob.location = loc; bpy.context.view_layer.update(); mw = ob.matrix_world.copy()
        ob.parent = arm; ob.parent_type = 'BONE'; ob.parent_bone = osso
        bpy.context.view_layer.update(); ob.matrix_world = mw
    return arm, [o for o, _ in pezzi]

def triangoli(objs):
    return sum(len(p.vertices) - 2 for o in objs if o.type == 'MESH' for p in o.data.polygons)

def run():
    coll = bpy.data.collections.get('Omino_Cartone')
    if coll:
        for o in list(coll.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0:
                (bpy.data.armatures if isinstance(d, bpy.types.Armature) else bpy.data.meshes).remove(d)
    else:
        coll = bpy.data.collections.new('Omino_Cartone'); bpy.context.scene.collection.children.link(coll)
    M = materiali()
    a0, o0 = costruisci(coll, M, Vector((6.0, 0, 0)), False)
    a1, o1 = costruisci(coll, M, Vector((7.2, 0, 0)), True)
    # tre comparse: stessa mesh del LOD1, colore dei vestiti per istanza
    for i, col in enumerate(((0.70, 0.22, 0.12, 1), (0.20, 0.38, 0.55, 1), (0.42, 0.52, 0.30, 1))):
        mv = mat_vernice(f'CB_P_Vestiti_{i+1}', col, 0.74, SCALA*1.5)
        for o in o1:
            c = o.copy(); c.parent = None; c.matrix_world = Matrix.Translation((1.0*(i + 1), 0, 0)) @ o.matrix_world
            c.name = o.name.replace('OM1_', f'OM1_Comparsa{i+1}_'); coll.objects.link(c)
            for s in c.material_slots:
                if s.material and s.material.name == 'CB_P_Vestiti': s.link = 'OBJECT'; s.material = mv
    return triangoli(o0), triangoli(o1)

if __name__ == '__main__':
    print(run())
