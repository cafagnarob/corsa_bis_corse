# =====================================================================
# cb_export_borgo.py — Corsa Bis · export delle palazzine del borgo (centro storico)
# Cosa fa (file PROVA CENTRO STORICO aperto, palazzine P1..P8 generate con
#   cb_borgo.run_campioni()):
#   - prepara(): per ogni palazzina unisce tutte le istanze del kit in UNA mesh
#     (colori per oggetto compresi), origine all'angolo in basso a destra della
#     facciata, davanti +X; nuovo atlante UV. Costruisce anche il LOD1: un
#     guscio chiuso (inviluppo convesso del corpo e della sopraelevazione),
#     senza buchi né dettagli, pochi triangoli.
#   - bake(i): LOD0 = colore dei cartoni cotto in un'immagine 1024;
#     LOD1 = colore del LOD0 proiettato sul guscio (selected to active) 256:
#     finestre, balconi e tende restano disegnati.
#   - esporta(): models/edifici/borgo.glb (JPEG, Draco), nodi Borgo_<i>_LOD0 e
#     Borgo_<i>_LOD1 + Borgo_Panni_LOD0 (filo da tendere sopra i vicoli, 4 m
#     lungo -Y), e borgo.json con larghezza/profondità/altezza di ognuna.
#   Metri reali (nel gioco scala 5,2 come gli altri modelli).
# Uso: Run Script, oppure passo per passo: prepara(); bake(1) ... ; esporta().
# =====================================================================
import bpy, bmesh, math, os, json
from mathutils import Matrix

SEMI = range(1, 9)                 # palazzine P1..P8 della collezione Borgo_Campione
RIS_LOD0, RIS_LOD1 = 1024, 256
CAMPIONI = 8
DETTAGLI = ('Persiana', 'Panni', 'Antenna', 'Balcone', 'Scala', 'Pianerottolo', 'Pensilina', 'Tenda',
            'Insegna', 'Comignolo', 'Serbatoio')          # fuori dal guscio del LOD1 (ma cotti sopra)

def cartella():
    t = bpy.data.texts.get('cb_export_borgo.py')
    radice = os.path.dirname(os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath))))
    return os.path.join(radice, 'packages', 'web', 'public', 'models', 'edifici')

def discendenti(o):
    out = []
    for c in o.children: out += [c] + discendenti(c)
    return out

def unisci(nome, sorgenti, inv, coll):
    # una copia per oggetto, coi materiali effettivi (anche quelli assegnati all'oggetto), poi join
    copie = []
    for o in sorgenti:
        if o.type != 'MESH': continue
        me = o.data.copy(); me.materials.clear()
        for sl in o.material_slots: me.materials.append(sl.material)
        me.transform(inv @ o.matrix_world)
        if me.uv_layers: me.uv_layers[0].name = 'UVMap'
        else: me.uv_layers.new(name='UVMap')
        c = bpy.data.objects.new('tmp', me); coll.objects.link(c); copie.append(c)
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for c in copie: c.select_set(True)
    bpy.context.view_layer.objects.active = copie[0]; bpy.ops.object.join()
    ob = copie[0]; ob.name = ob.data.name = nome
    return ob

def atlante(ob, margine=0.002):
    me = ob.data; at = me.uv_layers.new(name='Atlante'); me.uv_layers.active = at
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margine, area_weight=0.0, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')

def guscio(nome, gruppi, inv, coll):
    # LOD1: inviluppo convesso di ogni gruppo di pareti/tetti, facce complanari fuse, fondo tolto
    bm = bmesh.new()
    for g in gruppi:
        b2 = bmesh.new()
        for o in g:
            for v in o.data.vertices: b2.verts.new(inv @ o.matrix_world @ v.co)
        r = bmesh.ops.convex_hull(b2, input=b2.verts)
        via = {v for v in r['geom_interior'] + r['geom_unused'] if isinstance(v, bmesh.types.BMVert)}
        bmesh.ops.delete(b2, geom=list(via), context='VERTS')
        bmesh.ops.dissolve_limit(b2, angle_limit=math.radians(2), verts=b2.verts, edges=b2.edges)
        me2 = bpy.data.meshes.new('tmp'); b2.to_mesh(me2); b2.free(); bm.from_mesh(me2); bpy.data.meshes.remove(me2)
    fondo = [f for f in bm.faces if f.normal.z < -0.99 and max(v.co.z for v in f.verts) < 0.05]
    bmesh.ops.delete(bm, geom=fondo, context='FACES')
    bmesh.ops.triangulate(bm, faces=bm.faces)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(nome, me); coll.objects.link(ob); return ob

def prepara():
    c = bpy.data.collections.get('Export_Borgo')
    if c:
        for o in list(c.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d and d.users == 0: bpy.data.meshes.remove(d)
    else:
        c = bpy.data.collections.new('Export_Borgo'); bpy.context.scene.collection.children.link(c)
    c.hide_viewport = False
    for im in [i for i in bpy.data.images if i.name.startswith('Borgo_')]: bpy.data.images.remove(im)
    info = {}
    for i in SEMI:
        r = bpy.data.objects[f'P{i}']; inv = r.matrix_world.inverted(); figli = [o for o in discendenti(r) if o.type == 'MESH']
        l0 = unisci(f'X_Borgo_{i}_LOD0', figli, inv, c); atlante(l0)
        corpo = [o for o in figli if not any(d in o.name for d in DETTAGLI)]
        gruppi = [[o for o in corpo if '_Sopra' not in o.name], [o for o in corpo if '_Sopra' in o.name]]
        l1 = guscio(f'X_Borgo_{i}_LOD1', [g for g in gruppi if g], inv, c); atlante(l1, 0.01)
        l0.location = l1.location = r.location                  # sovrapposti per il bake
        # ingombro del corpo (senza panni, scale, balconi): è quello che il codice usa per affiancare le case
        V = [v.co for v in l1.data.vertices]
        info[f'Borgo_{i}'] = {'larghezza': round(-min(v.y for v in V), 2), 'profondita': round(-min(v.x for v in V), 2),
                              'altezza': round(max(v.co.z for v in l0.data.vertices), 2)}
    # filo di panni del kit (per i vicoli)
    k = bpy.data.objects['Panni_4m']; p = unisci('X_Borgo_Panni_LOD0', [k], k.matrix_world.inverted(), c); atlante(p)
    p.location = k.location
    bpy.data.texts.get('cb_export_borgo.py')['info'] = json.dumps(info)
    return info

def materiale(nome, im):
    mat = bpy.data.materials.get(nome) or bpy.data.materials.new(nome); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = im
    nt.links.new(t.outputs['Color'], b.inputs['Base Color']); nt.links.new(b.outputs[0], out.inputs['Surface'])
    b.inputs['Roughness'].default_value = 0.9
    return mat

def _bake_su(ob, im, sorgente=None, distanza=0.9):
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = CAMPIONI
    sc.render.bake.margin = 4; sc.render.bake.use_clear = True
    nodi = []
    if sorgente is None:                       # bake di se stesso: un nodo immagine in ogni materiale
        for m in ob.data.materials:
            nd = m.node_tree.nodes.new('ShaderNodeTexImage'); nd.image = im
            for x in m.node_tree.nodes: x.select = False
            nd.select = True; m.node_tree.nodes.active = nd; nodi.append((m, nd))
    for o in bpy.context.view_layer.objects: o.select_set(False)
    if sorgente is not None:
        sorgente.select_set(True)
        sc.render.bake.use_selected_to_active = True; sc.render.bake.cage_extrusion = 0.35; sc.render.bake.max_ray_distance = distanza
    else:
        sc.render.bake.use_selected_to_active = False
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
    sc.render.bake.use_selected_to_active = False
    for m, nd in nodi: m.node_tree.nodes.remove(nd)
    im.pack()

def finisci(ob, mat):
    me = ob.data; me.materials.clear(); me.materials.append(mat)
    for p in me.polygons: p.material_index = 0; p.use_smooth = False
    if 'UVMap' in me.uv_layers: me.uv_layers.remove(me.uv_layers['UVMap'])
    me.uv_layers['Atlante'].name = 'UVMap'

def bake(i):
    # i = numero della palazzina, oppure 'Panni'
    l0 = bpy.data.objects[f'X_Borgo_{i}_LOD0']
    me = l0.data; me.uv_layers.active = me.uv_layers['Atlante']; me.uv_layers['UVMap'].active_render = True
    im0 = bpy.data.images.new(f'Borgo_{i}_colore', RIS_LOD0 if i != 'Panni' else 256, RIS_LOD0 if i != 'Panni' else 256)
    _bake_su(l0, im0); finisci(l0, materiale(f'Borgo_{i}_LOD0', im0))
    l1 = bpy.data.objects.get(f'X_Borgo_{i}_LOD1')
    if l1:
        l1.data.materials.clear(); m1 = materiale(f'Borgo_{i}_LOD1', None); l1.data.materials.append(m1)
        im1 = bpy.data.images.new(f'Borgo_{i}_LOD1_colore', RIS_LOD1, RIS_LOD1)
        nd = next(n for n in m1.node_tree.nodes if n.type == 'TEX_IMAGE'); nd.image = im1; m1.node_tree.nodes.active = nd
        _bake_su(l1, im1, sorgente=l0); finisci(l1, m1)
    return i

def esporta():
    c = bpy.data.collections['Export_Borgo']; obs = list(c.objects); vecchi = {}
    for o in obs:
        vecchi[o.name[2:]] = o.location.copy(); o.location = (0, 0, 0); o.name = o.name[2:]
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in obs: o.select_set(True)
    d = cartella(); os.makedirs(d, exist_ok=True); p = os.path.join(d, 'borgo.glb')
    bpy.ops.export_scene.gltf(filepath=p, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
                              export_animations=False, export_lights=False, export_cameras=False,
                              export_image_format='JPEG', export_jpeg_quality=88,
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    with open(os.path.join(d, 'borgo.json'), 'w', encoding='utf-8') as f:
        f.write(bpy.data.texts['cb_export_borgo.py'].get('info', '{}'))
    tri = {}
    for o in obs:
        n = o.name; tri[n] = sum(len(f.vertices) - 2 for f in o.data.polygons)
        o.name = 'X_' + n; o.location = vecchi[n]
    c.hide_viewport = True
    return p, round(os.path.getsize(p)/1e6, 2), tri

def run():
    prepara()
    for i in list(SEMI) + ['Panni']: bake(i)
    return esporta()

if __name__ == '__main__':
    print(run())
