# =====================================================================
# cb_tessere_glb.py — Corsa Bis · pezzi delle tessere per il gioco (.glb)
# Cosa fa (file TESSERE aperto, richiede cb_lib.py e cb_tessera.py):
#   1. STRATO e CIMA in due LOD:
#      - LOD0 = le mesh del prototipo (bordi storti, onda sul bordo):
#        Tessera_Strato (548 tr) e Tessera_Cima_erba (500 tr);
#      - LOD1 = bordi dritti, stesso esagono e stesse UV: da media
#        distanza in su (bordi dritti a media distanza, GDD);
#   2. RAMPE tra tessere di quota diversa: viale, urbana, stretta, per un
#      salto di 1 e di 2 strati (6 pezzi, ognuno in LOD0 e LOD1);
#   3. scrive packages/web/public/models/tessere/tessere.glb: solo
#      geometria e UV, i materiali sono segnaposto col NOME dello slot
#      (Faccia, Bordo, Interno, Strada, Marciapiede, Striscia, Fianco):
#      il codice li sostituisce per nome.
# Convenzioni (GDD, Geometria delle tessere nel gioco):
#   - unità di gioco; UV della faccia superiore in unità (repeat = 1/32);
#   - strato: origine al centro della faccia INFERIORE, z 0..12;
#     cima: origine al centro della faccia inferiore, z 0..2;
#   - rampa: origine sul connettore (punto medio del lato) a quota della
#     tessera BASSA (z = 0 = faccia della sua cima); la rampa scende verso
#     −X, dentro la tessera bassa, e in x = 0 arriva alla quota della
#     tessera alta (+12,2 per strato: 12 di strato + 0,2 di stacco).
#     Nel gioco: posizione = connettore del lato della tessera bassa che
#     guarda la tessera alta, rotation.y = angolo del lato (lato 0 = 0°,
#     lato k = k·60°), così +X punta verso la tessera alta.
# Uso: Run Script.
# =====================================================================
import bpy, math, os
from mathutils import Vector, Matrix

def _carica(nome):
    t = bpy.data.texts.get(nome)
    if t is not None: return t.as_string()
    raise FileNotFoundError(nome + ': aprilo nel Text Editor')

_nome = __name__; __name__ = 'cb_tessere_glb'
if 'build_panel' not in globals(): exec(_carica('cb_lib.py'))
if 'mesh_strato' not in globals(): exec(_carica('cb_tessera.py'))
__name__ = _nome

QUOTA_STRATO = STRATO + STACCO            # 12,2: salto di quota tra due livelli
PENDENZA = 5.0                            # lunghezza della rampa = 5 x dislivello (circa 11°)
STRADE = {   # larghezza totale, marciapiede per lato (GDD, tabella delle strade)
    'viale':   (100.0, 13.6),
    'urbana':  (55.0, 9.3),
    'stretta': (30.0, 4.0)}
Z_STRADA, SP = 0.2, 0.3                   # come le strade di cb_basi: foglio a +0,2 spesso 0,3
LINEA = 0.8                               # larghezza delle strisce di carta (15 cm x 5,2)
S_RAMPA = 5.0                             # scala del cartone (come S_STRADA)

def slot(nome, col):
    m = bpy.data.materials.get('GLB_' + nome) or bpy.data.materials.new('GLB_' + nome)
    m.diffuse_color = col; m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'); b.inputs['Base Color'].default_value = col
    return m

def materiali_glb():
    # nomi fissi: il codice cerca questi (senza il prefisso GLB_, che glTF tiene: vedi resoconto)
    return {'faccia': slot('Faccia', (0.55, 0.42, 0.28, 1)), 'bordo': slot('Bordo', (0.45, 0.33, 0.2, 1)),
            'interno': slot('Interno', (0.3, 0.22, 0.14, 1)), 'strada': slot('Strada', (0.3, 0.3, 0.31, 1)),
            'marciapiede': slot('Marciapiede', (0.62, 0.59, 0.54, 1)), 'striscia': slot('Striscia', (0.86, 0.84, 0.78, 1)),
            'fianco': slot('Fianco', (0.5, 0.38, 0.25, 1))}

# ---------- strato e cima ----------
def pezzo(nome, geos, mats, coll):
    ob = make_object(nome, geos, mats, coll); ob.location = (0, 0, 0)
    for p in ob.data.polygons: p.use_smooth = False
    return ob

def strato_cima(coll, G):
    out = []
    # LOD0: copia delle mesh del prototipo (non tocco gli originali)
    M = materiali_tessera()
    for nome, me in (('Strato_LOD0', mesh_strato(M)), ('Cima_LOD0', mesh_cima(M, 'erba'))):
        m2 = me.copy(); m2.name = nome
        for i, k in enumerate(('faccia', 'bordo', 'interno')): m2.materials[i] = G[k]
        ob = bpy.data.objects.new(nome, m2); coll.objects.link(ob); out.append(ob)
    # LOD1: bordi dritti, stesso esagono (strato raggio 200, cima 199,4)
    for nome, r, t, sc in (('Strato_LOD1', RAGGIO, STRATO, S_STRATO), ('Cima_LOD1', RAGGIO - 0.6, CIMA, S_CIMA)):
        g = build_panel(esagono(r), t=t, rough=0, warp=0, nick=0, step=10000, scala=sc)
        out.append(pezzo(nome, [(g, Matrix())], [G['faccia'], G['bordo'], G['interno']], coll))
    return out

# ---------- rampe ----------
def rampa(tipo, salti, coll, G, lod=0):
    larg, marc = STRADE[tipo]; h = salti*QUOTA_STRATO; L = PENDENZA*h
    ang = math.atan2(h, L); lung = math.hypot(L, h); hw = larg/2
    det = dict(rough=0.6, nick=0.8, step=4.0, scala=1.0) if lod == 0 else dict(rough=0, nick=0, step=10000, scala=1.0)
    geos = []
    # corpo a cuneo: profilo nel piano X-Z estruso lungo Y per tutta la larghezza
    # (le due facce triangolari sono i fianchi di cartone, il nastro del bordo fa
    # pendio, fondo e testata)
    prof = [(-L, 0.0), (0.0, 0.0), (0.0, h)]
    g = build_panel(prof, t=larg, warp=0, seed=salti, **det)
    V, F, Mi, U, S = g
    geos.append(((V, F, [{0: 6, 1: 1, 2: 6}[m] for m in Mi], U, S), frame((0, hw, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))))
    # fogli sul pendio: sistema locale con u lungo la salita, v lungo Y, normale perpendicolare al pendio
    u = Vector((math.cos(ang), 0, math.sin(ang))); n = Vector((-math.sin(ang), 0, math.cos(ang)))
    def foglio(v0, v1, z, t, mat, s0=0.0, s1=None, seed=0):
        s1 = lung if s1 is None else s1
        gg = build_panel(rect(s0, v0, s1, v1), t=t, warp=0, seed=seed, **det)
        V2, F2, M2, U2, S2 = gg
        o = Vector((-L, 0, 0)) + n*z
        geos.append(((V2, F2, [{0: mat, 1: 1, 2: 2}[m] for m in M2], U2, S2), frame(tuple(o), tuple(u), (0, 1, 0), tuple(n))))
    foglio(-hw, hw, Z_STRADA, SP, 3, seed=1)                                   # carreggiata
    for sg in (-1, 1):                                                          # marciapiedi
        a, b = sorted((sg*hw, sg*(hw - marc)))
        foglio(a, b, Z_STRADA + SP + 0.05, SP, 4, seed=2 + sg)
    zs = Z_STRADA + SP + 0.05
    if tipo == 'viale':
        for c in (-1.5, 1.5): foglio(c - LINEA/2, c + LINEA/2, zs, 0.05, 5, seed=5)
        if lod == 0:
            for c in (-18.2, 18.2):
                s = 0.0
                while s < lung:
                    foglio(c - LINEA/2, c + LINEA/2, zs, 0.05, 5, s, min(lung, s + 15.0), seed=6); s += 30.0
    elif tipo == 'urbana' and lod == 0:
        s = 0.0
        while s < lung:
            foglio(-LINEA/2, LINEA/2, zs, 0.05, 5, s, min(lung, s + 15.0), seed=7); s += 30.0
    mats = [G['faccia'], G['bordo'], G['interno'], G['strada'], G['marciapiede'], G['striscia'], G['fianco']]
    return pezzo(f'Rampa_{tipo}_{salti}_LOD{lod}', geos, mats, coll)

# ---------- export ----------
def cartella_glb():
    t = bpy.data.texts.get('cb_tessere_glb.py')
    radice = os.path.dirname(os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath))))
    return os.path.join(radice, 'packages', 'web', 'public', 'models', 'tessere')

def run(esporta=True):
    nome = 'Tessere_GLB'
    coll = bpy.data.collections.get(nome)
    if coll:
        for o in list(coll.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d and d.users == 0: bpy.data.meshes.remove(d)
    else:
        coll = bpy.data.collections.new(nome); bpy.context.scene.collection.children.link(coll)
    G = materiali_glb(); obs = strato_cima(coll, G)
    for tipo in STRADE:
        for salti in (1, 2):
            for lod in (0, 1): obs.append(rampa(tipo, salti, coll, G, lod))
    # in Blender li metto in fila per guardarli (nel .glb la posizione si ignora: il codice usa la geometria)
    for i, o in enumerate(obs): o.location = (900 + (i % 4)*450, 600 + (i//4)*450, 0)
    tri = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in obs}
    if not esporta: return tri
    cart = cartella_glb(); os.makedirs(cart, exist_ok=True); path = os.path.join(cart, 'tessere.glb')
    vecchie = {o.name: o.location.copy() for o in obs}
    for o in obs: o.location = (0, 0, 0)                  # ogni pezzo con la sua origine nell'origine del .glb
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in obs: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
                              export_texcoords=True, export_normals=True, export_materials='EXPORT',
                              export_image_format='NONE', export_animations=False, export_lights=False, export_cameras=False,
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    for o in obs: o.location = vecchie[o.name]
    return path, round(os.path.getsize(path)/1e6, 2), tri

if __name__ == '__main__':
    print(run())
