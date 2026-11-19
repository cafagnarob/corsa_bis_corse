# =====================================================================
# cb_export_palina.py — Corsa Bis · export della palina in .glb
# Cosa fa (file PROVA PALINA aperto, palina già costruita con cb_palina.py):
#   per ogni LOD (Palina_LOD0/1/2) crea una mesh con origine alla base
#   dell'asta (davanti +X, la strada corre lungo X) fatta di DUE parti:
#   - corpo (asta, cartellino, targhe, scritta FERMATA del LOD0): il
#     cartone procedurale viene cotto (bake, solo colore) in un'immagine
#     sola su un atlante UV nuovo -> materiale "Palina"
#   - spago (nodo + spezzoni): NON cotto, materiale "Spago" crema neutro
#     con le UV del tubo (u attorno, v lungo lo spago in metri): il
#     codice lo copia per linea e ne cambia il colore
#   Scrive packages/web/public/models/arredo/palina.glb (JPEG, Draco).
#   Nodi nel .glb: Palina_LOD0, Palina_LOD1, Palina_LOD2 (tutti
#   nell'origine), ognuno una mesh con due primitive (Palina, Spago).
# Uso: Run Script.
# =====================================================================
import bpy, bmesh, math, os
from mathutils import Matrix, Vector

RISOLUZIONE = {0: 2048, 1: 512, 2: 256}
CAMPIONI = 16

def cartella():
    t = bpy.data.texts.get('cb_export_palina.py')
    radice = os.path.dirname(os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath))))
    return os.path.join(radice, 'packages', 'web', 'public', 'models', 'arredo')

def coll_export():
    c = bpy.data.collections.get('Export_Palina')
    if c:
        for o in list(c.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d and d.users == 0: bpy.data.meshes.remove(d)
    else:
        c = bpy.data.collections.new('Export_Palina'); bpy.context.scene.collection.children.link(c)
    for im in [i for i in bpy.data.images if i.name.startswith('Palina_LOD')]: bpy.data.images.remove(im)
    return c

def mesh_locale(src):
    # copia della mesh del LOD + scritte (FONT figli) in coordinate della base dell'asta
    dg = bpy.context.evaluated_depsgraph_get(); inv = src.matrix_world.inverted()
    bm = bmesh.new(); bm.from_mesh(src.data); mats = list(src.data.materials)
    for ch in src.children:
        if ch.type != 'FONT': continue
        me = bpy.data.meshes.new_from_object(ch.evaluated_get(dg))
        me.transform(inv @ ch.matrix_world)
        m = ch.material_slots[0].material
        if m not in mats: mats.append(m)
        for p in me.polygons: p.material_index = mats.index(m)
        if not me.uv_layers: me.uv_layers.new(name='UVMap')
        bm.from_mesh(me); bpy.data.meshes.remove(me)
    out = bpy.data.meshes.new('tmp'); bm.to_mesh(out); bm.free()
    for m in mats: out.materials.append(m)
    return out

def dividi(me, nome, coll):
    # corpo (tutto tranne lo spago) e spago in due oggetti
    spago_i = [i for i, m in enumerate(me.materials) if m and m.name == 'CB_Palina_Spago'][0]
    def parte(tieni_spago, n):
        m2 = me.copy(); m2.name = n; bm = bmesh.new(); bm.from_mesh(m2)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if (f.material_index == spago_i) != tieni_spago], context='FACES')
        bm.to_mesh(m2); bm.free()
        o = bpy.data.objects.new(n, m2); coll.objects.link(o); return o
    return parte(False, nome), parte(True, nome + '_spago')

def atlante(ob):
    me = ob.data; me.uv_layers[0].name = 'UVMap'
    at = me.uv_layers.new(name='Atlante'); me.uv_layers.active = at; me.uv_layers['UVMap'].active_render = True
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, area_weight=0.0, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')

def bake(ob, L):
    r = RISOLUZIONE[L]; sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = CAMPIONI
    sc.render.bake.margin = max(2, r//256); sc.render.bake.use_clear = True
    im = bpy.data.images.new(f'Palina_LOD{L}_colore', r, r); nodi = []
    for m in ob.data.materials:
        n = m.node_tree.nodes.new('ShaderNodeTexImage'); n.image = im
        for x in m.node_tree.nodes: x.select = False
        n.select = True; m.node_tree.nodes.active = n; nodi.append((m, n))
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
    for m, n in nodi: m.node_tree.nodes.remove(n)
    im.pack()
    mat = bpy.data.materials.get('Palina') or bpy.data.materials.new('Palina'); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = im
    nt.links.new(t.outputs['Color'], b.inputs['Base Color']); nt.links.new(b.outputs[0], out.inputs['Surface'])
    b.inputs['Roughness'].default_value = 0.85
    mat_l = bpy.data.materials.new(f'Palina_LOD{L}'); mat_l.use_nodes = True
    mat_l.node_tree.nodes.clear()
    o2 = mat_l.node_tree.nodes.new('ShaderNodeOutputMaterial'); b2 = mat_l.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    t2 = mat_l.node_tree.nodes.new('ShaderNodeTexImage'); t2.image = im
    mat_l.node_tree.links.new(t2.outputs['Color'], b2.inputs['Base Color']); mat_l.node_tree.links.new(b2.outputs[0], o2.inputs['Surface'])
    b2.inputs['Roughness'].default_value = 0.85
    me = ob.data; me.materials.clear(); me.materials.append(mat_l)
    for p in me.polygons: p.material_index = 0
    me.uv_layers.remove(me.uv_layers['UVMap']); me.uv_layers['Atlante'].name = 'UVMap'

def mat_spago():
    m = bpy.data.materials.get('Spago') or bpy.data.materials.new('Spago'); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (0.86, 0.82, 0.74, 1); b.inputs['Roughness'].default_value = 0.95
    return m

def prepara():
    coll = coll_export(); out = []
    for L in range(3):
        src = bpy.data.objects[f'Palina_LOD{L}']
        me = mesh_locale(src)
        corpo, spago = dividi(me, f'X_Palina_LOD{L}', coll); bpy.data.meshes.remove(me)
        spago.data.materials.clear(); spago.data.materials.append(mat_spago())
        for p in spago.data.polygons: p.material_index = 0; p.use_smooth = L < 2
        spago.data.uv_layers[0].name = 'UVMap'
        atlante(corpo); out.append((L, corpo, spago))
    return out

def finisci(L):
    corpo = bpy.data.objects[f'X_Palina_LOD{L}']; spago = bpy.data.objects[f'X_Palina_LOD{L}_spago']
    # unisco lo spago nel corpo: una mesh, due materiali (Palina_LODn, Spago)
    for o in bpy.context.view_layer.objects: o.select_set(False)
    corpo.select_set(True); spago.select_set(True); bpy.context.view_layer.objects.active = corpo
    bpy.ops.object.join()
    corpo.location = (0, 0, 0); return corpo

def esporta():
    coll = bpy.data.collections['Export_Palina']
    # nel .glb i nodi devono chiamarsi Palina_LOD0..2: scambio i nomi con gli originali per l'export
    scambi = []
    for L in range(3):
        a = bpy.data.objects[f'Palina_LOD{L}']; b = bpy.data.objects[f'X_Palina_LOD{L}']
        a.name = f'_src_Palina_LOD{L}'; b.name = f'Palina_LOD{L}'; scambi.append((a, b, L))
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in coll.objects: o.select_set(True)
    c = cartella(); os.makedirs(c, exist_ok=True); p = os.path.join(c, 'palina.glb')
    bpy.ops.export_scene.gltf(filepath=p, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
                              export_animations=False, export_lights=False, export_cameras=False,
                              export_image_format='JPEG', export_jpeg_quality=88,
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    for a, b, L in scambi: b.name = f'X_Palina_LOD{L}'; a.name = f'Palina_LOD{L}'
    coll.hide_viewport = True
    tri = {o.name: sum(len(f.vertices) - 2 for f in o.data.polygons) for o in coll.objects}
    return p, round(os.path.getsize(p)/1e6, 2), tri

def run():
    prepara()
    for L in range(3): bake(bpy.data.objects[f'X_Palina_LOD{L}'], L)
    for L in range(3): finisci(L)
    return esporta()

if __name__ == '__main__':
    print(run())
